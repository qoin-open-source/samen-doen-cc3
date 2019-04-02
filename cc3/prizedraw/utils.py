import datetime
import logging
import random
import string
from decimal import Decimal

from rdoclient import RandomOrgClient

from django.conf import settings
from django.contrib import messages
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from cc3.core.models import Transaction
from cc3.cyclos import backends
from cc3.cyclos.common import TransactionException
from cc3.cyclos.models import User

from .models import Draw, Prize, TicketException, RepeatPurchase, \
    RepeatPurchaseTicket

LOG = logging.getLogger(__name__)


def check_user_can_buy_tickets(num_tickets, user, draw=None,
                               check_balance=True):
    """Check whether a user can buy the requested number of tickets in draw

    If draw is None, default to the "current" draw
    """
    if not draw:
        draw = get_current_draw()

    if not draw:
        raise TicketException(_(u"There is no Draw in progress"))

    num_can_buy = draw.max_tickets_user_can_buy(user)
    if num_can_buy <= 0:
        raise TicketException(
            _(u"You have already bought the maximum of {0} tickets".format(
                draw.max_tickets_per_person)))
    if num_can_buy < num_tickets:
        per_person = draw.max_tickets_per_person
        if num_can_buy < per_person:
            raise TicketException(
                _(u"You already have {0} ticket(s), you can buy a maximum of "
                  u"{1} ticket(s) more".format(
                    (per_person-num_can_buy), num_can_buy)))

        raise TicketException(
            _(u"You can buy a maximum of {0} tickets".format(num_can_buy)))

    available_balance = backends.get_account_status(
        user.username).accountStatus.availableBalance
    if check_balance:
        ticket_cost = num_tickets * draw.ticket_price
        if ticket_cost > available_balance:
            raise TicketException(
                _(u"You don't have enough credit"))

    return True


def get_user_winnings(user):
    """Get number pf prizes and total winnings for user"""
    total_amount = 0.0
    prizes = Prize.objects.filter(winning_ticket__purchased_by=user)
    num_prizes = prizes.count()
    for prize in prizes:
        if prize.amount_paid:
            total_amount += float(prize.amount_paid)
        else:
            # payment is pending but add in the the amount
            # that will be paid
            total_amount += float(prize.amount_to_pay)
    return num_prizes, Decimal(total_amount)


def get_user_win_in_last_draw(user):
    """
    :param user: `User` to check
    :return: Has the `User` won in the draw before the current active draw?
    """
    last_draw = get_previous_draw()
    if last_draw:
        prizes = Prize.objects.filter(winning_ticket__purchased_by=user,
                                      draw=get_previous_draw())
        if prizes:
            return True

    return False


def get_total_winnings():
    """Get number of prizes, winners and total winnings for all users"""
    total_amount = 0.0
    prizes = Prize.objects.filter(winning_ticket__isnull=False)
    num_prizes = prizes.count()
    num_winners = len(set(
        [prize.winning_ticket.purchased_by for prize in prizes]))
    for prize in prizes:
        if prize.amount_paid:
            total_amount += float(prize.amount_paid)
        else:
            # payment is pending but add in the the amount
            # that will be paid
            total_amount += float(prize.amount_to_pay)
    return num_prizes, num_winners, Decimal(total_amount)


def get_current_draw():
    """Returns the current draw, if there is one"""
    now = timezone.now()
    draws_in_progress = Draw.objects.exclude(
        draw_ends__lt=now).exclude(
        draw_starts__gt=now).order_by('draw_ends')
    # TODO Log error if > 1 ??
    try:
        return draws_in_progress[0]
    except IndexError:
        return None


def get_previous_draw():
    """
    :return: The draw before the current active draw
    """
    now = timezone.now()
    draws = Draw.objects.exclude(draw_ends__gt=now).order_by('-draw_ends')

    try:
        return draws[0]
    except IndexError:
        return None


def choose_numbers(n, _max, _min):
    """Pick n distinct integers in the range (max, min) inclusive

    The calling code should handle any exception raised by random.org
    """
    r = RandomOrgClient(getattr(settings, "RANDOMDOTORG_API_KEY"))
    numbers = r.generate_integers(n=n, max=_max, min=_min, replacement=False)
    return numbers


def buy_tickets(data, sender, draw, request=None, bulk_purchase_override=False):
    """
    Buy tickets for 'sender' (User),
    :param data:

        'amount': price per ticket),
        'num_tickets': number of tickets to buy

    :param sender:
        Cyclos User (auth user proxy model)

    :param draw:
        draw to buy tickets from
    :param request:
        http request (only if messages need adding, ie cronjob doesn't use this)
    :param bulk_purchase_override:
        Allow user to buy more than Draw 'max_tickets_per_person'
    :return:
        list of tickets purchased
    """
    from .views import BuyTicketsFormView
    payment_made = False

    num_tickets = data['num_tickets']

    amount = Decimal(data['amount'])
    description = _(u'Direct purchase of Prize Draw tickets')
    transfer_type_id = getattr(
        settings, 'CYCLOS_PRIZEDRAW_TICKET_TRANSFER_TYPE_ID',
        BuyTicketsFormView.TRANSFER_TYPE_ID)

    try:
        # Cyclos transaction request.
        transaction = backends.to_system_payment(
            sender, amount, description, transfer_type_id)
        payment_made = True
        if request:
            messages.add_message(
                request, messages.SUCCESS, _('Payment made successfully.'))
    except TransactionException, e:
        error_message = _('Could not make payment at this time.')

        if 'NOT_ENOUGH_CREDITS' in e.args[0]:
            error_message = _('You do not have sufficient credit to '
                              'complete the payment.')
        if request:
            messages.add_message(request, messages.ERROR, error_message)
    else:
        try:
            # Log the payment (use bank user for the recipient)
            bank_user = User.objects.get(
                id=getattr(settings, 'CYCLOS_BANK_USER_ID'))
            Transaction.objects.create(
                amount=amount,
                sender=sender,
                receiver=bank_user,
                transfer_id=transaction.transfer_id,
            )
        except Exception, e:
            # Report this to ADMINS, but show success to user
            # because the payment was made
            message = u'Direct payment made (transfer id={0}), but '  \
                u'failed to create Transaction: {1}'.format(
                    transaction.transfer_id, e)
            LOG.error(message)

            if not settings.DEBUG:
                mail_admins(u'Failed to log payment',
                            message, fail_silently=True)

    if payment_made:
        tickets_purchased = []
        # create and allocate tickets for user
        for i in range(0, num_tickets):
            try:
                tickets_purchased.append(draw.get_new_ticket(
                    user=sender,
                    transfer_id=transaction.transfer_id,
                    when_purchased=transaction.created,
                    bulk_purchase_override=bulk_purchase_override
                ))
            except Exception, e:
                # Mail admins because payment taken but not
                # all tickets allocated
                admin_message = \
                    u'Direct payment made for draw ticket(s) but failed ' \
                    u'to allocate Ticket(s). The reason was:\n\n'  \
                    '"{1}"\n\n'  \
                    'Amount paid: {2}\n' \
                    'Number of tickets allocated: {3} of {4}\n' \
                    'Transfer id: {0}'.format(
                        transaction.transfer_id, e, amount, i, num_tickets)
                mail_admins(u'Failed to allocate draw ticket(s)',
                            admin_message, fail_silently=True)

                error_message = _("Failed to buy ticket: {0}".format(e))
                if request:
                    messages.error(request, error_message)
                return
        if request:
            messages.success(request, _(
                u"{0} tickets bought ".format(num_tickets)))

        return tickets_purchased


def setup_repeat_purchase(data, tickets_purchased, user, request=None):
    # setup repeat purchase entries for future ticket purchasing via cronjob
    repeat_purchase = RepeatPurchase.objects.create(
        purchased_by=user,
        when_purchased=datetime.datetime.now(),
        num_tickets=data['num_tickets'],
        num_months=data['num_months']
    )
    repeat_purchase.save()
    if tickets_purchased:
        for ticket in tickets_purchased:
            repeat_ticket_purchase = RepeatPurchaseTicket.objects.create(
                recurring_purchase=repeat_purchase,
                ticket=ticket
            )
            repeat_ticket_purchase.save()

    if request:
        messages.add_message(
            request, messages.SUCCESS,
            mark_safe(
                _('Repeat purchase for {0} tickets per month setup '
                  'successfully. Please remember to set up a '
                  '<a href="{1}">monthly standing order</a> now.'.format(
                    data['num_tickets'],
                    reverse('add-funds'))
                  )))


def disassociate_card(card_number):
    from cc3.cards.models import CardNumber  # , Card

    uid_number = CardNumber.objects.get(uid_number=card_number)

    # card = Card.objects.get(number=uid_number, owner__isnull=False)

    # clean up -
    # 1. get unique 50 digit UID
    test_number = ''.join(random.choice(
        string.ascii_uppercase + string.digits) for _ in range(50))
    test_number_unique = True

    while test_number_unique:
        try:
            CardNumber.objects.get(uid_number=test_number)
        except CardNumber.DoesNotExist:
            uid_number.uid_number = test_number
            uid_number.save()
            test_number_unique = False

    # 2. TODO: move cyclos user to 'removed' user group. another day :-!
