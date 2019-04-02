# encoding: utf-8
"""
Available resources:

NFC Card machine, and B£ website access

/api/v1/prizedraws/card/<card-identifier>/payment/
/api/v1/prizedraws/card/<card-identifier>/credit/
/api/v1/prizedraws/login/


/api/v1/prizedraws/validate_user_can_buy/
/api/v1/prizedraws/register_new_user/
/api/v1/prizedraws/credit_user/
/api/v1/prizedraws/purchase_tickets/
"""
import logging
from decimal import Decimal
from cc3.prizedraw.utils import get_current_draw, disassociate_card
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.core.mail import mail_admins
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from rest_framework import status, views
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cc3.cyclos import backends
from cc3.cyclos.models import User
from cc3.cards.models import Terminal, Operator, Card, CardNumber
from cc3.cards.nice_pass import nicepass
from cc3.cards.views_api import CardTransactionView, load_class

from .forms import (
    ValidateUserNumTicketsForm, PrizeDrawCreditUserForm, PrizeDrawNewUserForm,
    PrizeDrawPurchaseTicketsForm, PrizeDrawCreditNewUserForm)

from .models import TicketException
from .utils import check_user_can_buy_tickets

LOG = logging.getLogger(__name__)


class CardPrizeDrawPaymentView(CardTransactionView):
    """
    POST-only, Token authentication required

    Given the sender ID, receiver ID and num_tickets purchase prize draw
    tickets.

    If the transaction is valid return a HTTP 200 OK and return the transaction
    ID.

    If the transaction could not take place return a HTTP 400/401 with the
    reason why the transaction could not proceed:
    - invalid sender id
    - invalid receiver id
    - invalid number of tickets
    - sender balance not sufficient

    Example POST data:

    {
      "terminal_name": "my_terminal_identifier",
      "operator_name": "operator-name",
      "sender_id": 12,
      "receiver_id": 13,
      "num_tickets": 5,
    }
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    TRANSFER_TYPE_ID = 46  # override in settings if necessary

    def __init__(self, **kwargs):
        self.draw = get_current_draw()
        super(CardPrizeDrawPaymentView, self).__init__(**kwargs)

    def _buy_tickets(self, data):
        num_tickets = data['num_tickets']
        transaction = data['transaction']

        # create and allocate tickets for user
        for i in range(0, num_tickets):
            try:
                self.draw.get_new_ticket(
                    user=transaction.sender,
                    transfer_id=transaction.transfer_id,
                    when_purchased=transaction.date_created
                )
            except Exception, e:
                # Mail admins because payment taken but not
                # all tickets allocated
                admin_message = u'Direct payment made for draw ticket(s) but ' \
                                u'failed to allocate Ticket(s). The reason ' \
                                u'was:\n\n' \
                                u'"{1}"\n\n' \
                                u'Amount paid: {2}\n' \
                                u'Number of tickets allocated: {3} of {4}\n' \
                                u'Transfer id: {0}'.format(
                                    transaction.transfer_id, e,
                                    transaction.amount, i, num_tickets)
                mail_admins(u'Failed to allocate draw ticket(s)',
                            admin_message, fail_silently=True)

                error_message = _("Failed to buy ticket: {0}".format(e))
                return Response({'detail': error_message},
                                status=status.HTTP_400_BAD_REQUEST)

        return transaction

    def post(self, request, card_number):
        LOG.info(u'Prize Draw ticket purchase')

        if not self.draw:
            msg = _(u'There is no draw in progress')
            LOG.info(u"{}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # get the purchaser of the tickets
        try:
            sender = User.objects.get(id=request.data['sender_id'])
        except User.DoesNotExist:
            sender = None

        num_tickets = int(request.data['num_tickets'])

        # check they can buy the number of tickets they want
        try:
            check_user_can_buy_tickets(num_tickets, sender, draw=self.draw)
        except TicketException, e:
            LOG.info(u"{}".format(e.message))
            return Response({'detail': e.message},
                            status=status.HTTP_400_BAD_REQUEST)

        # Perform the transaction.
        data = {
            'terminal_name': request.data['terminal_name'],
            'operator_name': request.data['operator_name'],
            'sender_id': request.data['sender_id'],
            'receiver_id': request.data['receiver_id'],
            'amount': u"{0}".format(
                Decimal(num_tickets * self.draw.ticket_price)),
            'num_tickets': num_tickets,
            'description': u"Prize Draw {0} purchase of {1} ticket(s)".format(
                           self.draw, request.data['num_tickets'])
        }
        transfer_type_id = getattr(
            settings,
            'CYCLOS_PRIZEDRAW_NFC_TICKET_TRANSFER_TYPE_ID',
            self.TRANSFER_TYPE_ID)
        transaction = self._make_transaction(
            sender, data, card_number, transfer_type_id)

        if isinstance(transaction, Response):
            # Transaction failed. Return 400 request response.
            return transaction

        data['transaction'] = transaction['card_transaction']
        prizedraw_ticket = self._buy_tickets(data)
        if isinstance(prizedraw_ticket, Response):
            # Transaction failed. Return 400 request response.
            return prizedraw_ticket

        # return transaction_id (as per other payment methods, as 'success')
        return Response({'transaction_id': transaction['transaction_id']})


class CardPrizeDrawCreditUserView(views.APIView):
    """
    IMPORTANT - THIS IS ONLY EVER USED FOR ANONYMOUS NEW CARD USERS
    Given the business ID, customer ID and amount, allow NFC app to give
    'credit' from reserve account to customer, balanced by a payment from a
    business account to the reserve account

    If the transaction is valid return a HTTP 200 OK and return the transaction
    ID.

    If the transaction could not take place return a HTTP 400/401 with the
    reason why the transaction could not proceed:
    - invalid customer id
    - invalid business id
    - invalid amount
    - business balance not sufficient

    Example POST data:

    {
      "terminal_name": "my_terminal_identifier",
      "operator_name": "operator-henk",
      "customer_id": 12,
      "business_id": 13,
      "amount": 20,
      "description": "Positoos payment",
    }


    """
    RESERVE_TO_CUSTOMER_TRANSFER_TYPE_ID = 32
    BUSINESS_TO_RESERVE_TRANSFER_TYPE_ID = 36

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def _make_transactions(self, request_user, data, card_number,
                           reserve_to_customer_transfer_type_id,
                           business_to_reserve_transfer_type_id):
        """

        """
        try:
            terminal = Terminal.objects.get(
                name=data.get('terminal_name', ''))
            operator = Operator.objects.get(
                name=data.get('operator_name', ''),
                business=terminal.business)
        except (Terminal.DoesNotExist, Operator.DoesNotExist):
            msg = _(u'Terminal or operator name invalid')
            LOG.info(u"1: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)
        LOG.info(u"Terminal user ID {}".format(terminal.business.id))
        LOG.info(u"Operator user ID {}".format(operator.business.id))
        LOG.info(u"Authentication user ID {}".format(request_user.id))

        if request_user.id != terminal.business.id != operator.business.id:
            msg = _(u'Terminal or operator name invalid')
            LOG.info(u"2: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        sender = get_object_or_404(User, id=data.get('sender_id', ''))
        uid_number = get_object_or_404(CardNumber, uid_number=card_number)
        card = get_object_or_404(Card, number=uid_number, owner__isnull=False)
        receiver = get_object_or_404(
            User, id=data.get('receiver_id', ''))
        raw_amount = data.get('amount', 0)
        if raw_amount.find('.') == -1:
            amount = int(raw_amount)
        else:
            amount = Decimal(raw_amount)

        LOG.info(u"Sender ID {}".format(sender.id))
        LOG.info(u"Receiver ID {}".format(receiver.id))
        LOG.info(u"Amount {}".format(amount))
        LOG.info(u"Card User ID {}".format(card.owner.id))

        if not amount or Decimal(amount) <= 0:
            msg = _(u'Invalid amount, must be positive')
            LOG.info(u"3: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        if receiver.id != request_user.id and sender.id != request_user.id:
            msg = _(u'Must be authenticated as either sending or '
                    u'receiving party')
            LOG.info(u"4: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        if receiver.id == sender.id:
            msg = _(u'Unable to create payment with same sender as receiver')
            LOG.info(u"5: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        if receiver.id != card.owner.id and sender.id != card.owner.id:
            msg = _(u'Card must be linked to one of the payment parties')
            LOG.info(u"6: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        if not sender.cc3_profile:
            msg = _(u'Sender doesn\'t have CC3 profile')
            LOG.info(u"8: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        max_amount = sender.cc3_profile.current_balance
        credit_limit = sender.cc3_profile.current_credit_limit()
        if credit_limit:
            max_amount += credit_limit

        if max_amount < amount:
            msg = _(u'Business has insufficient balance to buy customers '
                    u'bonus tickets')
            LOG.info(
                u"Max amount: {}".format(max_amount))
            LOG.info(u"7: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        LOG.info(u'Details valid, performing transactions between system and '
                 u'{0} and {1} and system for {2}'.format(
                    sender.id, receiver.id, amount))

        errors = []

        try:
            description = "Card payment credit from Sterling for " \
                          "ticket purchase"
            backends.from_system_payment(
                receiver.username,
                amount,
                description, reserve_to_customer_transfer_type_id
            )
        except Exception, e:
            message = \
                u'System to member payment attempted, receiver {0}), but ' \
                u'failed. Amount: {1}. Exception {2}'.format(
                    receiver.username, amount, e.message)
            LOG.error(message)
            if not settings.DEBUG:
                mail_admins(u'Failed to credit new card holder from reserve',
                            message, fail_silently=True)
            errors.append("Unable to credit customer account.")

        try:
            description = "Business sterling payment to reserve for " \
                          "ticket purchase"
            backends.to_system_payment(
                sender.username, amount,
                description, business_to_reserve_transfer_type_id
            )
        except Exception, e:
            message = \
                u'member to system payment attempted, business {0}), but ' \
                u'failed. Amount: {1}. Exception {2}'.format(sender.username,
                                                             amount, e.message)
            LOG.error(message)
            if not settings.DEBUG:
                mail_admins(u'Failed to credit reserve from business account',
                            message, fail_silently=True)
            errors.append("Unable make credit reserve account from business.")

        if errors:
            return Response(
                {'detail': u", ".join(errors)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return {}

    def post(self, request, card_number):

        # check new user isn't trying to buy more than the max for the draw
        credit_new_user_form = PrizeDrawCreditNewUserForm(request.data)
        if credit_new_user_form.is_valid():

            LOG.info(u'Prize Draw card credit new user')

            reserve_to_customer_transfer_type_id = getattr(
                settings, 'CYCLOS_RESERVE_TO_CUSTOMER_TRANSFER_TYPE_ID',
                CardPrizeDrawCreditUserView.RESERVE_TO_CUSTOMER_TRANSFER_TYPE_ID
            )
            business_to_reserve_transfer_type_id = getattr(
                settings, 'CYCLOS_BUSINESS_TO_RESERVE_TRANSFER_TYPE_ID',
                CardPrizeDrawCreditUserView.BUSINESS_TO_RESERVE_TRANSFER_TYPE_ID
            )

            # Perform the transactions.
            transaction = self._make_transactions(
                request.user, request.data, card_number,
                reserve_to_customer_transfer_type_id,
                business_to_reserve_transfer_type_id
            )

            if isinstance(transaction, Response):
                # Transaction failed. Return 400 request response.
                return transaction

            return Response({'success': True})
        else:
            disassociate_card(card_number)

            errors = credit_new_user_form.errors
            return Response(
                {'detail': u", ".join(errors)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PrizeDrawLoginView(views.APIView):
    """
    POST-only, No authentication required

    Given the prizedraw user name, check it exists in the database, and if so,
    authenticate.
    If valid, return a HTTP 200 OK and return the token for
    using the other resources.
    If not valid, return a HTTP 400 Bad Request response with the message:
    - "Invalid prize draw user", if the prizedraw user could not be found.

    Used by B£ website PHP to 'login' for PayPal ticket purchases

    Example POST data:

    {
      "name": "prizedraw_identifier"
    }

    """
    permission_classes = ()

    def post(self, request):
        LOG.info(u'PrizeDraw token collection')
        try:
            user = authenticate(username=request.data.get('username', ''),
                                password=request.data.get('password', ''))
        except MultipleObjectsReturned:
            user = None
        except ValidationError:
            user = None

        if not user:
            msg = u'Invalid prize draw user'
            LOG.info(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # Terminal has been found, create a Token for it
        (token, created) = Token.objects.get_or_create(user=user)

        if created:
            LOG.info(u'Created token: {0}'.format(user.id))
        else:
            LOG.info(u'Reusing token: {0}'.format(user.id))

        return Response({'token': token.key})


class ValidateUserCanBuyView(views.APIView):
    """
    View to check email address can be X num_tickets in the current prize draw,
    for PayPal offsite ticket purchase
    """
    authentication_classes = (TokenAuthentication,)

    def post(self, request):
        LOG.info(u'Prize Draw validate user')

        form = ValidateUserNumTicketsForm(data=request.data)
        if form.is_valid():
            data = {
                'can_buy': True,
                'need_new_user': form.need_new_user
            }
            return Response(data)
        else:
            data = {
                'can_buy': False,
                'need_new_user': False,
                'error': form.errors
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)


class RegisterNewUserView(views.APIView):
    """
    View to register new user based on email address only, so they can
    participate in PayPal offsite ticket purchase
    """
    authentication_classes = (TokenAuthentication,)

    def post(self, request):
        LOG.info(u'Prize Draw register new user')

        prize_draw_register_form = PrizeDrawNewUserForm(request.data)

        if not prize_draw_register_form.is_valid():
            msg = 'Email Address is not valid'
            LOG.error(msg)
            return Response({'error': 'Email Address is not valid'},
                            status=status.HTTP_400_BAD_REQUEST)

        backend = getattr(settings, 'CC3_PRIZEDRAW_API_NEW_ACCOUNT_VIEW', None)
        if not backend:
            LOG.error(u'Invalid configuration, '
                      u'CC3_PRIZEDRAW_API_NEW_ACCOUNT_VIEW '
                      u'needs to be defined in settings')
            return Response({'error': "Unable to create new accounts, "
                                      "denied by server"},
                            status=status.HTTP_400_BAD_REQUEST)

        LOG.info(u'Backend found')

        # Request and configuration valid, ready the data for the
        # auto-generated user account.
        view = load_class(backend)()
        LOG.info(u'Backend imported')

        temp_password = nicepass()

        LOG.info(u'Calling registration backend')
        cleaned_data = {'email': prize_draw_register_form.cleaned_data['email'],
                        'password_confirmation': temp_password}

        # Make use of the configured registration backend.
        try:
            user, profile = view.register(None, **cleaned_data)
        except Exception as e:
            msg = u'Unable to create new account, registration invalid'
            LOG.error(u'{0}: {1}'.format(msg, e))
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        if not user:
            msg = u'Unable to register new user account'
            LOG.error(msg)
            data = {'error': msg}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        LOG.info(u'User {0} created'.format(user))
        LOG.info(u'Profile {0} for user {1} created'.format(profile, user))

        data = {
            "username": user.username,
            "email": cleaned_data['email'],
            "password": temp_password
        }

        return Response(data)


class CreditUserView(views.APIView):
    """
    View to credit new user after a PayPal payment on the B£ website,
    so they can participate in PayPal offsite ticket purchase
    """
    authentication_classes = (TokenAuthentication,)
    TRANSFER_TYPE_ID = 32

    def post(self, request):
        LOG.info(u'Prize Draw credit user')

        prize_draw_credit_user_form = PrizeDrawCreditUserForm(request.data)
        transfer_type_id = getattr(
            settings, 'CYCLOS_PAYPAL_CREDIT_TRANSFER_TYPE_ID',
            CreditUserView.TRANSFER_TYPE_ID
        )
        if prize_draw_credit_user_form.is_valid():
            try:
                receiver_user = User.objects.get(
                    email=prize_draw_credit_user_form.cleaned_data['email']
                )
                description = "PayPal credit from Sterling for " \
                              "ticket purchase"
                backends.from_system_payment(
                    receiver_user.username,
                    prize_draw_credit_user_form.cleaned_data['amount'],
                    description, transfer_type_id
                )
            except Exception, e:
                message = u'System to member payment attempted, email {0}), ' \
                          u'but failed. Amount: {1}. Exception {2}'.format(
                            prize_draw_credit_user_form.cleaned_data['email'],
                            prize_draw_credit_user_form.cleaned_data['amount'],
                            e.message)
                LOG.error(message)
                if not settings.DEBUG:
                    mail_admins(u'Failed to credit prizedraw paypal payment',
                                message, fail_silently=True)

                return Response({'error': "Unable to credit account"},
                                status=status.HTTP_400_BAD_REQUEST)

        return Response('ok')


class PurchaseTicketsView(views.APIView):
    """
    'Buy' tickets for user identified by email
    Brixton Bonus website - NB PayPal
    """

    authentication_classes = (TokenAuthentication,)

    def __init__(self, **kwargs):
        self.draw = get_current_draw()
        super(PurchaseTicketsView, self).__init__(**kwargs)

    def post(self, request):
        from .utils import buy_tickets
        LOG.info(u'Prize Draw PAYPAL ticket purchase')

        if not self.draw:
            msg = _(u'There is no draw in progress')
            LOG.info(u"{}".format(msg))

        purchase_tickets_form = PrizeDrawPurchaseTicketsForm(request.data)
        if purchase_tickets_form.is_valid():
            # get the purchaser of the tickets
            try:
                sender = User.objects.get(
                    email=purchase_tickets_form.cleaned_data['email'])
            except User.DoesNotExist:
                sender = None

            num_tickets = int(purchase_tickets_form.cleaned_data['num_tickets'])

            # check they can buy the number of tickets they want
            try:
                check_user_can_buy_tickets(num_tickets, sender, draw=self.draw)
            except TicketException, e:
                LOG.info(u"{}".format(e.message))
                return Response({'detail': e.message},
                                status=status.HTTP_400_BAD_REQUEST)

            # Perform the transaction.
            data = {
                'amount': u"{0}".format(
                    Decimal(num_tickets * self.draw.ticket_price)),
                'num_tickets': num_tickets,
            }

            prizedraw_ticket = buy_tickets(data, sender, self.draw)
            if isinstance(prizedraw_ticket, Response):
                # Transaction failed. Return 400 request response.
                return prizedraw_ticket

            return Response({'success': True})
        return Response({'error': True})
