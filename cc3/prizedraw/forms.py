import logging

from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _

from .models import RepeatPurchase
from .utils import check_user_can_buy_tickets, TicketException
from cc3.cyclos.models import User

LOG = logging.getLogger(__name__)


class AwardPrizesForm(forms.Form):
    confirm = forms.BooleanField()


class BuyTicketsForm(forms.Form):
    """
    Form for buying tickets in the current Draw

    Validates that:
    1. User won't exceed max-tickets-per-user limit, and
    2. The amount is less than the user's available balance (ie
    balance + credit limit).
    """
    num_tickets = forms.IntegerField(label=_(u'Number of tickets to buy'))
    amount = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    repeat_purchase = forms.BooleanField(
        label=_(u'Set up monthly ticket-purchase'),
        required=False, help_text=_(
            u'If ticked, set up a monthly repeat purchase')
    )
    run_indefinitely = forms.BooleanField(
        label=_(u'Run indefinitely'), required=False)
    num_months = forms.IntegerField(label=_(u'Number of months to participate'),
                                    required=False)

    class Media:
        js = ('js/buy_tickets.js',)

    def __init__(self, *args, **kwargs):
        """Cache user and draw passed in"""
        self.user = kwargs.pop('user')
        self.draw = kwargs.pop('draw')
        super(BuyTicketsForm, self).__init__(*args, **kwargs)

    def clean_num_tickets(self):
        """Check user can buy this many tickets

        Check:
        1. max number allowed per user, and
        2. available credit
        """
        num_tickets = self.cleaned_data.get('num_tickets')
        try:
            check_user_can_buy_tickets(num_tickets, self.user, self.draw)
            return num_tickets
        except Exception, e:
            raise forms.ValidationError(
                _(u'You cannot buy {0} tickets: {1}').format(num_tickets,
                                                             e))

    def clean_repeat_purchase(self):
        data = self.cleaned_data['repeat_purchase']
        if data:
            num_repeat_purchases = RepeatPurchase.objects.filter(
                purchased_by=self.user,
                cancelled_date__isnull=True).count()

            max_repeat_purchases = getattr(
                settings, "PRIZE_DRAW_MAX_REPEAT_PURCHASES", 10)
            if num_repeat_purchases >= max_repeat_purchases:
                raise forms.ValidationError(
                    _(u"You cannot set up more than {0} active repeat "
                      u"purchases".format(max_repeat_purchases)))

        return data

    def clean(self):
        """Set amount to the cost of num_tickets tickets"""
        cleaned_data = super(BuyTicketsForm, self).clean()
        num_tickets = cleaned_data.get('num_tickets', '')
        if num_tickets:
            cleaned_data['amount'] = num_tickets * self.draw.ticket_price

        repeat_purchase = self.cleaned_data.get('repeat_purchase', None)
        run_indefinitely = self.cleaned_data.get('run_indefinitely', None)
        num_months = self.cleaned_data.get('num_months', None)

        # prevent invalid input with checkboxes
        if (repeat_purchase and not (run_indefinitely or num_months)) or \
                (repeat_purchase and run_indefinitely and num_months):
            raise forms.ValidationError(
                _(u'If you would like to set up a repeat purchase, please '
                  u'tick the "Run indefinitely" checkbox * or * enter a number '
                  u'into the "Number of months to participate" box')
            )

        if (not repeat_purchase and run_indefinitely) or \
                (not repeat_purchase and num_months):
            raise forms.ValidationError(
                _(u'If you would like to set up a repeat purchase, please '
                  u'tick the "Set up monthly ticket-purchase" checkbox')
            )

        return cleaned_data


class CancelRepeatPurchaseForm(forms.Form):

    pk = forms.IntegerField(min_value=1)

    def __init__(self, *args, **kwargs):
        """Cache user passed in"""
        self.user = kwargs.pop('user')
        self.instance = None
        super(CancelRepeatPurchaseForm, self).__init__(*args, **kwargs)

    def clean(self):
        """
        Validate that the user 'owns' the repeat purchase
        """
        try:
            self.instance = RepeatPurchase.objects.get(
                pk=self.cleaned_data['pk'])

            if self.user.pk != self.instance.purchased_by.pk:

                raise forms.ValidationError(
                    _(u"Only the owner of the ticket can cancel the repeat "
                      u"purchase"))
        except RepeatPurchase.DoesNotExist:
            raise forms.ValidationError(
                _(u"Only the owner of the ticket can cancel the repeat "
                  u"purchase"))

        return self.cleaned_data


class ValidateUserNumTicketsForm(forms.Form):
    """
    Form to validated PayPal offsite ticket purchase
    """
    num_tickets = forms.IntegerField()
    email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        super(ValidateUserNumTicketsForm, self).__init__(*args, **kwargs)
        self.need_new_user = False

    def clean_num_tickets(self):
        data = self.cleaned_data

        if data['num_tickets'] <= 0:
            raise forms.ValidationError("Number of tickets must be greater "
                                        "than 0")

        return data['num_tickets']

    def clean(self):
        data = self.cleaned_data

        # user exists?
        try:
            user = User.objects.get(email=data['email'])
            num_tickets = data['num_tickets']
            # don't worry about users balance, as this is for PayPal check
            # where user is adding money to an account to purchase the tickets
            check_user_can_buy_tickets(num_tickets, user, check_balance=False)

        except User.DoesNotExist:
            # don't want to raise an exception if user doesn't exist
            # this means that a user will be created by the PayPal
            # transactions
            self.need_new_user = True
        except TicketException, e:
            raise forms.ValidationError("{0}".format(e.message))

        return self.cleaned_data


class PrizeDrawNewUserForm(forms.Form):
    email = forms.EmailField()


class PrizeDrawCreditUserForm(forms.Form):
    email = forms.EmailField()
    amount = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)


class PrizeDrawCreditNewUserForm(forms.Form):
    sender_id = forms.IntegerField()
    receiver_id = forms.IntegerField()
    terminal_name = forms.CharField()
    operator_name = forms.CharField()
    amount = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)

    def clean_amount(self):
        """
        Validate that the amount is <= price of current draw tickets * max num
        :return:

        """
        from .utils import get_current_draw
        data = self.cleaned_data['amount']

        draw = get_current_draw()
        num_can_buy = draw.max_tickets_per_person
        ticket_price = draw.ticket_price

        if data > num_can_buy * ticket_price:
            raise forms.ValidationError(
                _(u"You can buy a maximum of {0} tickets".format(num_can_buy)))


class PrizeDrawPurchaseTicketsForm(forms.Form):
    email = forms.EmailField()
    num_tickets = forms.IntegerField(min_value=1)
