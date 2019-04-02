"""
Available resources:

/api/v1/cards/terminal/login/
/api/v1/cards/operator/login/
/api/v1/cards/user/login/
/api/v1/cards/card/
/api/v1/cards/card/<card-identifier>/
/api/v1/cards/card/<card-identifier>/payment/

"""
import importlib
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import status, views
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cc3.cyclos import backends
from cc3.cyclos.common import TransactionException
from cc3.cyclos.models import User, CC3Profile, CyclosGroup
from cc3.rewards.transactions import cause_reward
from cc3.rewards.models import BusinessCauseSettings

from cc3.cards.models import CARD_STATUS_ACTIVE

from .models import (
    Terminal, Operator, CardNumber, Card, CardType, CardTransaction)
from .nice_pass import nicepass

from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError
from cc3.rest.http import JSONResponse
from cc3.cards.models import Fulfillment

LOG = logging.getLogger(__name__)


# TODO: Add APIViewSet as per other APIs (accounts, marketplace), so that all
# authentication and permission classes can be included in a more DRY way
# serializer classes less important? (ie API doesn't have any bulk Card actions)


def load_class(full_class_string):
    """
    Dynamically load a class from a string.
    """

    class_data = full_class_string.split(".")
    module_path = ".".join(class_data[:-1])
    class_str = class_data[-1]

    module = importlib.import_module(module_path)
    # Finally, we retrieve the Class
    return getattr(module, class_str)


def register_card(card_number, user, status=CARD_STATUS_ACTIVE):
    """
    Register a new card from the given user.

    :param card_number: ``uid_number`` of the card to be registered (must be a
    ``CardNumber`` object, previously created).
    :param user: The ``User`` owner of the card.
    :return: The ``Card`` object created if everything went well. ``None`` if
    the operation failed due to some DB inconsistency.
    """

    # Get default CardType or create a new one
    try:
        card_type = CardType.objects.get(default=True)
    except CardType.DoesNotExist:
        card_type = CardType.objects.create(name='Default type', default=True)

    try:
        card = Card.objects.create(
            number=card_number, card_type=card_type, owner=user,
            status=status)

        # Card has been registered
        LOG.info(u'Card registered: {0}'.format(card.id))

        return card
    except IntegrityError:
        LOG.error(u'Fail when trying to assign a used card number ({0}'.format(
            card_number))
        return None


def get_new_card_number(card_id):
    auto_create_card_numbers = getattr(
        settings, "CC3_AUTO_CREATE_CARD_NUMBERS", False)
    if not auto_create_card_numbers:
        return

    # system configured to auto create card numbers
    card_number_auto_start_number = getattr(
        settings, "CC3_AUTO_CREATE_CARD_START", 50000)

    # get highest number in db above auto start
    try:
        highest_number = CardNumber.objects.filter(
            number__gte=card_number_auto_start_number
        )[0]
        new_number = highest_number.number + 1
    except IndexError:
        new_number = card_number_auto_start_number

    card_number, created = CardNumber.objects.get_or_create(
        uid_number=card_id,
        number=new_number
    )
    return card_number


class TerminalLoginView(views.APIView):
    """
    POST-only, No authentication required

    Given the name of a terminal, check if the name exists in our database.
    If valid, return a HTTP 200 OK and return the terminal ID and a token for
    using the other resources.
    If not valid, return a HTTP 400 Bad Request response with the message:
    - "Invalid terminal name", if the terminal could not be found.
    - "Terminal has not yet been registered" if the terminal does not have a
      user.

    Example POST data:

    {
      "name": "my_terminal_identifier"
    }

    """
    permission_classes = ()

    def post(self, request):
        LOG.info(u'Terminal login')
        terminal = None
        if 'name' in request.data:
            try:
                terminal = Terminal.objects.get(name=request.data['name'])
            except Terminal.DoesNotExist:
                terminal = Terminal.objects.create(name=request.data['name'],
                                                   business=None)

            terminal.last_seen_date = timezone.now()
            terminal.save()

        if not terminal.business:
            msg = u'Terminal has not yet been registered to your account, ' \
                  u'please do so via the website'
            LOG.info(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # Terminal has been found, create a Token for it
        (token, created) = Token.objects.get_or_create(user=terminal.business)

        if created:
            LOG.info(u'Created token: {0}'.format(terminal.id))
        else:
            LOG.info(u'Reusing token: {0}'.format(terminal.id))
        business_name = u''
        try:
            business_name = unicode(
                terminal.business.get_profile().business_name)
        except:
            pass

        return Response(
            {'token': token.key, 'id': terminal.id, 'name': business_name})


class OperatorLoginView(views.APIView):
    """
    POST-only, Token authentication required

    Given the name and pin of an operator, check if any of the operators
    registered to the same business as the terminal (via Token ID) exist and
    if the pin is correct.
    If valid, return a HTTP 200 OK and return the operator ID.
    If not valid (no operator exists or if the pin is incorrect) return a HTTP
    400 Bad Request response with the message: "Invalid operator or pin".

    Example POST data:

    {
      "name": "operator-henk",
      "pin": "1234"
    }
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        operator = None
        LOG.info(u'Operator login')
        name = request.data.get('name', '')
        pin = request.data.get('pin', '')
        LOG.info(name)
        LOG.info(pin)

        if name != '' and pin != '':
            try:
                operator = Operator.objects.get(name=name,
                                                pin=pin,
                                                business=request.user)
            except Operator.DoesNotExist:
                pass
        if not operator:
            msg = u'Invalid operator or pin'
            LOG.info(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # Operator has been found
        LOG.info(u'Operator {0} found'.format(operator.id))
        operator.last_login_date = timezone.now()
        operator.save()

        return Response({'id': operator.id, 'user_id': operator.business.id})


class UserLoginView(views.APIView):
    """
    POST-only, Token authentication required

    Given the email address and password of a user, check if the given user
    exists in the system and if logging in is possible.
    If valid, return a HTTP 200 OK and return the user ID
    If not valid return a HTTP 403 Forbidden response with the message:
    "Invalid email address or password".

    Example POST data:

    {
      "email": "user@example.com",
      "password": "secret"
    }
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        LOG.info(u'User login')
        try:
            user = authenticate(username=request.data.get('email', ''),
                                password=request.data.get('password', ''))
        except MultipleObjectsReturned:
            user = None
            LOG.critical(u'Email address {0} active in multiple users'.format(
                request.data.get('email')))
        except ValidationError:
            user = None

        if not user:
            msg = u'Invalid email address or password'
            LOG.info(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # User has been found
        LOG.info(u'User {0} found'.format(user.id))
        return Response({'id': user.id})


class CardRegisterView(views.APIView):
    """
    POST-only, Token authentication required

    Given the user ID and card number create a new Card for the given user.
    If valid, return a HTTP 200 OK and return the card ID.
    If not valid return a HTTP 403 Forbidden response with the message: "Unable
    to register card".

    {
      "card": "CARDID123",
      "user_id": 12
    }
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        LOG.info(u'Card registration')
        msg = u'Unable to register card'
        card_id = request.data.get('card', '')
        user_id = request.data.get('user_id', '')

        if not card_id or not user_id:
            LOG.info(u"1: " + msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            card_number = CardNumber.objects.get(uid_number=card_id)
            # this isn't reached if card number doesn't exist
            user = User.objects.get(id=user_id)
        except CardNumber.DoesNotExist:
            card_number = get_new_card_number(card_id)

            if not card_number:
                LOG.info(u"2: Unable to register card. "
                         u"Card number {0} does not exist".format(card_id))
                return Response({'detail': msg},
                                status=status.HTTP_400_BAD_REQUEST)

            # the user wasn't retrieved above, so get it now
            user = User.objects.get(id=user_id)

            LOG.info(u'Card registration: auto created {0}'.format(card_number))
            LOG.info(u'Card registration: new number {0}'.format(
                card_number.number))

        except User.DoesNotExist:
            LOG.info(u"2: Unable to register card. User {0} does not "
                     u"exist".format(user_id))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        card = register_card(card_number, user)
        if not card:
            return Response(
                {'detail': u'This card number is already registered.'},
                status=status.HTTP_409_CONFLICT)

        return Response({'id': card.id})


class CardDetailView(views.APIView):
    """
    GET-only, Token authentication required

    Given the card number return the details of the card and the user of the
    card.
    If no card exists with the given number return a HTTP 400 Bad request.

    Example GET response:

    {
      "user_name": "Piet Hein",
      "user_id": 12,
      "balance": 30
    }
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, card_number):
        LOG.info(u'Card details')
        try:
            uid_number = CardNumber.objects.get(uid_number=card_number)
            card = Card.objects.get(number=uid_number)
        except (CardNumber.DoesNotExist, Card.DoesNotExist) as e:
            msg = _(u'Card does not exist')
            LOG.info(u'{0}: {1}'.format(msg, e))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        if not card.is_active:
            msg = _(u'Card is blocked or not yet activated')
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)


        cc3_profile = card.owner.get_cc3_profile()
        if not cc3_profile:
            msg = _(u'User does not have a CC3 Profile, unable to handle '
                    u'transactions')
            LOG.info(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        reward_percentage = u''
        reward_type = u''
        if 'cc3.rewards' in settings.INSTALLED_APPS:
            # Apply rewards.
            reward_percentage = Decimal("5.00")
            reward_type = 'percentage'
            try:
                business_settings = BusinessCauseSettings.objects.get(
                    user=request.user)
                if not business_settings.reward_percentage:
                    reward_type = 'fixed'
                elif business_settings.transaction_percentage > 0:
                    reward_percentage = business_settings.transaction_percentage
            except BusinessCauseSettings.DoesNotExist:
                LOG.error(u'Business {0} has no settings defined'.format(
                    request.user))

            LOG.info(u'Owner reward settings: {0}, {1}'.format(
                reward_type, reward_percentage))
            LOG.info(u'Sending details of card {0}'.format(card_number))

        active_tickets = 0
        remaining_tickets = 0
        win_in_last_draw = False
        prizedraw_active = False
        prizedraw_active_days = 0
        ticket_price = Decimal(1.0)
        if 'cc3.prizedraw' in settings.INSTALLED_APPS:
            from cc3.prizedraw.utils import get_current_draw, \
                get_user_win_in_last_draw
            next_draw = get_current_draw()
            if next_draw:
                active_tickets = next_draw.tickets.filter(
                    purchased_by=card.owner).count()
                remaining_tickets = max(0,
                        next_draw.max_tickets_user_can_buy(card.owner))
                ticket_price = Decimal(next_draw.ticket_price)
                prizedraw_active = True
                prizedraw_active_days = next_draw.active_days()

            win_in_last_draw = get_user_win_in_last_draw(card.owner)
        try:
            return Response({'name': cc3_profile.full_name,
                             'first_name': cc3_profile.first_name,
                             'username': card.owner.username,
                             'card_number': card.number.number,
                             'user_id': card.owner.id,
                             'reward_type': reward_type,
                             'reward_percentage': unicode(reward_percentage),
                             'balance': cc3_profile.current_balance,
                             'active_tickets': active_tickets,
                             'remaining_tickets': remaining_tickets,
                             'win_in_last_draw': win_in_last_draw,
                             'prizedraw_active': prizedraw_active,
                             'prizedraw_active_days': prizedraw_active_days,
                             'ticket_price': ticket_price
            })
        except:
            msg = u'User has not been configured properly / Cyclos unavailable'
            LOG.error(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)


class CardPermittedDetailView(views.APIView):
    """
    GET-only, Token authentication required

    Given the card number return if registering the card is possible or not

    Example GET response:

    {
      "card_number": "12345",
      "card_uid": "ABCDEF",
    }
    
        
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, card_number):
        LOG.info(u'Card permitted')
        # TODO: Refactor this and Registation and NewUserReg - so that card
        # TODO: logic is in model not view or 'helpers'
        try:
            card_nr = CardNumber.objects.get(uid_number=card_number)
        except CardNumber.DoesNotExist as e:
            card_nr = get_new_card_number(card_number)
            # if a card_nr is returned then system configured to auto create new
            if not card_nr:
                msg = u'Card not permitted'
                LOG.info(u'{0}: {1}'.format(msg, e))
                return Response({'detail': msg},
                                status=status.HTTP_400_BAD_REQUEST)
        # if Card exists but is blocked, return error message
        try:
            card = card_nr.card
            if not card.is_active:
                msg = _(u'Card is blocked or not yet activated')
                return Response({'detail': msg},
                                status=status.HTTP_400_BAD_REQUEST)
        except Card.DoesNotExist:
            pass

        return Response({"card_number": "{0:05d}".format(card_nr.number),
                         "card_uid": card_nr.uid_number})


class NewAccountView(views.APIView):
    """
    POST-only, Token authentication required

    Given the card number attempt to register a new user account with this card

    Example POST response:

    {
      "card_number": "12345",
      "card_uid": "ABCDEF",
      "username": "my-username",
      "password": "foobar123",
    }
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, card_number):
        LOG.info(u'New account')
        try:
            card_nr = CardNumber.objects.get(uid_number=card_number)
        except CardNumber.DoesNotExist as e:
            # try and get new CardNumber object
            card_nr = get_new_card_number(card_number)
            if not card_nr:
                msg = u'Card not permitted'
                LOG.info(u'{0}: {1}'.format(msg, e))
                return Response({'detail': msg},
                                status=status.HTTP_400_BAD_REQUEST)

        LOG.info(u'Creating account')

        backend = getattr(settings, 'CC3_CARDS_API_NEW_ACCOUNT_VIEW', None)
        if not backend:
            LOG.error(u'Invalid configuration, CC3_CARDS_API_NEW_ACCOUNT_VIEW '
                      u'needs to be defined in settings')
            return Response(
                {'detail': "Unable to create new accounts, denied by server"},
                status=status.HTTP_400_BAD_REQUEST)
        LOG.info(u'Backend found')

        # Request and configuration valid, ready the data for the
        # auto-generated user account.
        view = load_class(backend)()
        LOG.info(u'Backend imported')

        # Get the business community to create the new card user in it.
        try:
            business = CC3Profile.objects.get(user=request.user)
        except CC3Profile.DoesNotExist:
            LOG.error(u'Business profile for user {0} does not exist'.format(
                request.user))
            msg = u'Unable to create new account, business invalid'
            LOG.error(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # community_id = getattr(settings, 'DEFAULT_COMMUNITY_ID', 1)
        # LOG.info(u'Attempting to get community {0}'.format(community_id))
        community = business.community
        if not community:
            LOG.error(u'Business profile {0} does not have a community'.format(
                business.pk))
            msg = u'Unable to create new account, no community available'
            LOG.error(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        LOG.info(u"Community: {0}".format(community))

        email = getattr(settings, 'CC3_CARDS_API_EMAIL_POSTFIX', 'example.org')
        email = u'{0}@{1}'.format(card_nr.number, email)
        temp_password = nicepass()

        LOG.info(u'Calling registration backend')
        cleaned_data = {'community': community,
                        'card_number': card_nr.number,
                        'email': email,
                        'password_confirmation': temp_password}

        # Make use of the configured registration backend.
        try:
            user, profile = view.register(None, **cleaned_data)
        except Exception as e:
            msg = u'Unable to create new account, registration invalid'
            LOG.error(u'{0}: {1}'.format(msg, e))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        if not user:
            msg = u'Unable to register new user account'
            LOG.error(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)
        LOG.info(u'User {0} created'.format(user))
        LOG.info(u'Profile {0} for user {1} created'.format(profile, user))

        if not register_card(card_nr, user):
            return Response(status=status.HTTP_409_CONFLICT)

        LOG.info(u"Card registered to new user")

        return Response({"card_number": unicode(card_nr.number),
                         "card_uid": card_nr.uid_number,
                         "username": user.username,
                         "email": email,
                         "password": temp_password})


class CardTransactionView(views.APIView):
    """
    Generic ``APIView`` implementation to handle NFC card transactions.

    Implements the ``_make_transaction`` method, which takes care of validate
    the data and perform the requested transaction.

    Transaction related API views can subclass this view and implement their
    custom ``post`` method by calling the ``_make_transaction`` on it.
    TODO: put the validation login into a Form for reuse elsewhere in the system
    (or even as part of a model)
    """
    def _make_transaction(
        self, request_user, data, card_number, transfer_type_id=None):
        """
        Validates the given data in a POST request for a transaction. Then,
        performs the transaction and returns the transaction data to the
        caller or a 404 ``Response`` object ready to be returned by the
        ``post`` method if the transaction failed.

        This method should be called in the beginning of the ``post`` methods
        of subclassed transaction views. Then, you can make custom operations
        after the transaction or return the error response in case the
        transaction didn't succeeded.

        :param request: ``Request`` object representing the POST request
        for a transaction.
        :param card_number: ``uid_number`` of the ``CardNumber`` object of
        the card involved in the transaction.

        :return transaction_data: dict object including the next keys:
            ``card_transaction``: ``Transaction`` object representing the
            performed transaction with all the transaction data.
            ``transaction_id``: integer value which is the ID of the Cyclos
            performed transaction.
        """
        # TODO: Refactor to use Django REST framework serializers
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

        description = data.get('description', '')

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
            msg = _(
                u'Must be authenticated as either sending or receiving party')
            LOG.info(u"4: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        if not card.is_active:
            # actually, Blocked or Pending, but effectively not usable
            msg = _(u'Card is blocked or not yet activated')
            LOG.info(u"10: {}".format(msg))
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

        sender_cc3_profile = sender.cc3_profile

        # If INTER_COMMUNITIES_TRANSACTIONS not enabled,
        # check sender and receiver are in same community
        operator_cc3_profile = operator.business.cc3_profile
        inter_communities_transactions_allowed = \
            operator_cc3_profile.inter_communities_transactions_allowed()

        if not inter_communities_transactions_allowed:
            if sender_cc3_profile.community != receiver.cc3_profile.community:
                msg = _(u'You cannot make transactions outside your community')
                LOG.info(u"9: {}".format(msg))
                return Response({'detail': msg},
                                status=status.HTTP_400_BAD_REQUEST)

        max_amount = sender_cc3_profile.current_balance
        credit_limit = sender_cc3_profile.current_credit_limit()
        if credit_limit:
            max_amount += credit_limit

        if max_amount < amount:
            msg = _(u'Sender has insufficient balance for the payment')
            LOG.info(
                u"Max amount: {}".format(max_amount))
            LOG.info(u"7: {}".format(msg))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # check a charity isn't getting rewarded by a business
        if getattr(settings, "BUSINESS_TO_CHARITY_REWARD_CHECK", False):
            try:
                business_cyclos_group = CyclosGroup.objects.get(
                    name=settings.CYCLOS_BUSINESS_MEMBER_GROUP)

                charity_cyclos_group = CyclosGroup.objects.get(
                    name=settings.CYCLOS_CHARITY_MEMBER_GROUP)

                if sender.cc3_profile.cyclos_group == \
                        business_cyclos_group and \
                        receiver.cc3_profile.cyclos_group == \
                        charity_cyclos_group:
                    msg = _(u"Spaardoelen kunnen geen waardering van "
                            u"Winkeliers of Instellingen ontvangen")

                    LOG.info(u"11: {}".format(msg))
                    return Response({'detail': msg},
                                    status=status.HTTP_400_BAD_REQUEST)
            except CyclosGroup.DoesNotExist:
                LOG.critical('Charity causes Cyclos group does not exist.')

        # check a charity isn't getting rewarded by a business
        if getattr(settings, "INSTITUTION_TO_CHARITY_REWARD_CHECK", False):
            try:
                institution_cyclos_group = CyclosGroup.objects.get(
                    name=settings.CYCLOS_INSTITUTION_MEMBER_GROUP)

                charity_cyclos_group = CyclosGroup.objects.get(
                    name=settings.CYCLOS_CHARITY_MEMBER_GROUP)

                if sender.cc3_profile.cyclos_group == \
                        institution_cyclos_group and \
                        receiver.cc3_profile.cyclos_group == \
                        charity_cyclos_group:
                    msg = _(u"Spaardoelen kunnen geen waardering van "
                            u"Winkeliers of Instellingen ontvangen")

                    LOG.info(u"12: {}".format(msg))
                    return Response({'detail': msg},
                                    status=status.HTTP_400_BAD_REQUEST)
            except CyclosGroup.DoesNotExist:
                LOG.critical('Charity causes Cyclos group does not exist.')

        LOG.info(u'Details valid, performing transaction between {0} and '
                 u'{1} for {2}'.format(sender.id, receiver.id, amount))
        try:
            LOG.info(u'Details valid, performing transaction {0} '
                     u'(transfer_type_id: {1})'.format(
                        description, transfer_type_id))
            transaction = backends.user_payment(
                sender, receiver, amount, description, transfer_type_id)
        except TransactionException as e:
            msg = _(u'Unable to perform the transaction')
            LOG.warning(u'{0}: {1}'.format(msg, e))
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # Register the transaction.
        LOG.info(u'Cyclos transaction complete')
        card_transaction = CardTransaction.objects.create(
            operator=operator, terminal=terminal, card=card,
            description=description, amount=amount, sender=sender,
            receiver=receiver, transfer_id=transaction.transfer_id)
        LOG.info(u'Details stored as card transaction {0}'.format(
            card_transaction.pk))

        return {'card_transaction': card_transaction,
                'transaction_id': transaction.transfer_id}


class CardPaymentView(CardTransactionView):
    """
    POST-only, Token authentication required

    Given the sender ID, receiver ID, amount and description perform the given
    transaction.
    If the transaction is valid return a HTTP 200 OK and return the transaction
    ID.

    If the transaction could not take place return a HTTP 400/401 with the
    reason why the transaction could not proceed:
    - invalid sender id
    - invalid receiver id
    - invalid amount
    - sender balance not sufficient

    Example POST data:

    {
      "terminal_name": "my_terminal_identifier",
      "operator_name": "operator-henk",
      "sender_id": 12,
      "receiver_id": 13,
      "amount": 20,
      "description": "Positoos payment",
    }
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, card_number):
        LOG.info(u'Card payment')

        # Perform the transaction.
        transaction = self._make_transaction(
            request.user, request.data, card_number
        )

        if isinstance(transaction, Response):
            # Transaction failed. Return 400 request response.
            return transaction

        return Response({'transaction_id': transaction['transaction_id']})


class CardRewardView(CardTransactionView):
    """
    POST-only, Token authentication required

    Given the sender ID, receiver ID, amount and description perform the given
    transaction from business to consumer. Then, perform another transaction
    from consumer to the selected cause, which will be the reward.

    If the transaction is valid return a HTTP 200 OK and return the transaction
    ID.

    If the transaction could not take place return a HTTP 400/401 with the
    reason why the transaction could not proceed:
    - invalid sender id
    - invalid receiver id
    - invalid amount
    - sender balance not sufficient

    Example POST data:

    {
      "terminal_name": "my_terminal_identifier",
      "operator_name": "operator-henk",
      "sender_id": 12,
      "receiver_id": 13,
      "amount": 20,
      "description": "Positoos payment",
    }
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, card_number):
        LOG.info(u'Reward payment')

        # Perform the transaction of reward from Business to Consumer.
        transaction = self._make_transaction(
            request.user, request.data, card_number)

        if isinstance(transaction, Response):
            # Transaction failed. Return 400 request response.
            return transaction

        card_transaction = transaction['card_transaction']

        # Compute donations from Consumer to Charity.
        reward = cause_reward(
            card_transaction.amount, card_transaction.receiver,
            card_transaction.transfer_id)

        if reward:
            reward_transaction = CardTransaction.objects.create(
                operator=card_transaction.operator,
                terminal=card_transaction.terminal,
                card=card_transaction.card,
                description=reward.description, amount=reward.amount,
                sender=reward.sender, receiver=reward.recipient,
                transfer_id=reward.transfer_id)
            LOG.info(u'Donation transferred.')

            good_cause = reward.recipient.get_cc3_profile()
            business_name = u''
            if good_cause:
                business_name = good_cause.business_name

            # 3047 - use punten instead of positoos. Not sure if this affects
            # front end, so altering manually here
            currency_name = u"punten"
            # getattr(
            #    settings, "CURRENCY_NAME",
            #    getattr(settings, "CC3_SYSTEM_NAME", "Punten"))
            details = _(u"{0} {1} were credited and the good cause {2} "
                        u"received {3} {4}").format(
                            int(card_transaction.amount -
                                reward_transaction.amount),
                            currency_name,
                            unicode(business_name),
                            int(reward_transaction.amount),
                            currency_name)

        else:
            reward_transaction = None
            currency_name = u"punten"
            # getattr(
            #    settings, "CURRENCY_NAME",
            #    getattr(settings, "CC3_SYSTEM_NAME", "Positoos"))
            details = _(u"{0} {1} were credited").format(
                card_transaction.amount, currency_name)

        return Response({
            'details': details,
            'card_transaction_id': transaction['transaction_id'],
            'reward_transaction_id': reward_transaction.transfer_id if reward_transaction else None
        })

@login_required
@permission_required('is_staff')
@require_http_methods(["POST"])
def update_fulfillment_status(request):
    error = False
    try:
        data = JSONParser().parse(request)
        if 'fid' in data and 'status' in data:
            f = Fulfillment.objects.get(id=data['fid'])
            f.status = data['status']
            f.save()
        else:
            error = True
    except Exception as e:
        error = True

    if error is False:
        return JSONResponse({
            'success': True,
        })
    else:
        return JSONResponse({
            'success': False,
        })