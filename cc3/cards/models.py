import logging

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import pgettext, ugettext_lazy as _

from cc3.billing.models import TerminalDeposit
from cc3.billing.utils import update_terminal_products
from cc3.core.models import Transaction
from cc3.cyclos.models.account import CC3Profile

from .validators import iccid_validator


LOG = logging.getLogger(__name__)
#
# Note: The Cards and CardTypes follow the Cyclos card structure to allow
# easier integration of the two in the future. Most of these fields are
# currently not in use and some go against Django best practices however
# only make changes if this does not interfere with the card/card_type
# tables in Cyclos.
#

# Note: I have yet to find the exact status codes in Cyclos

CARD_STATUS_ACTIVE = 'A'
CARD_STATUS_PENDING = 'P'
CARD_STATUS_BLOCKED = 'B'
CARD_STATUS_DENIED = 'D'
CARD_STATUS_CHOICES = (
    (CARD_STATUS_ACTIVE, _('Active')),
    (CARD_STATUS_PENDING, _('Pending')),
    (CARD_STATUS_BLOCKED, _('Blocked')),  # e.g. if lost
    (CARD_STATUS_DENIED, _('Denied')),   # e.g. admin denied application
)

CARD_REGISTRATION_CHOICE_OLD = 'Old'
CARD_REGISTRATION_CHOICE_SEND = 'Send'

CARD_REGISTRATION_CHOICES_FIRST = (
    (CARD_REGISTRATION_CHOICE_OLD, _('I have an old card to replace')),
    (CARD_REGISTRATION_CHOICE_SEND, _("Order a new card")),
    # translated to 'first card'
)

CARD_REGISTRATION_CHOICES = (
    (CARD_REGISTRATION_CHOICE_OLD, _('I have an old card to replace')),
    (CARD_REGISTRATION_CHOICE_SEND, _("Order another card")),
)

CARD_FULLFILLMENT_CHOICE_NEW = 'New'
CARD_FULLFILLMENT_CHOICE_MANUALLY_PROCESSED = 'Manually Processed'
CARD_FULLFILLMENT_CHOICE_ACCOUNT_CLOSED = 'Account Closed'
CARD_FULFILLMENT_STATUSES = (
    (CARD_FULLFILLMENT_CHOICE_NEW, pgettext('fulfillment', 'New')),
    (CARD_FULLFILLMENT_CHOICE_MANUALLY_PROCESSED, _('Manually Processed')),
    (CARD_FULLFILLMENT_CHOICE_ACCOUNT_CLOSED, _('Cancelled (Account closed)')),
)

CARD_NUMBER_VALIDATORS = [
    MaxValueValidator(getattr(settings, 'MAX_CARD_NUMBER', 9999999999999999)),
    MinValueValidator(getattr(settings, 'MIN_CARD_NUMBER', 0)),
]


class CardNumber(models.Model):
    uid_number = models.CharField(_('Card UID'), max_length=50, unique=True)
    number = models.BigIntegerField(
        _('Card number'), unique=True,
        validators=CARD_NUMBER_VALIDATORS,
        primary_key=True,
    )
    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-number',)

    def __unicode__(self):
        return str(self.number)


class CardType(models.Model):
    name = models.CharField(_('Card name'), max_length=100)
    default = models.BooleanField(
        default=True, help_text=u'The default type, used for newly registered '
                                u'Cards')
    # The following fields are not in use #
    card_format_number = models.CharField(max_length=56, blank=True, null=True)
    default_expiration_number = models.IntegerField(blank=True, null=True)
    default_expiration_field = models.IntegerField(blank=True, null=True)
    card_security_code = models.CharField(max_length=1, blank=True, null=True)
    show_card_security_code = models.BooleanField(default=False)
    ignore_day_in_expiration_date = models.BooleanField(default=False)
    min_card_security_code_length = models.IntegerField(blank=True, null=True)
    max_card_security_code_length = models.IntegerField(blank=True, null=True)
    security_code_block_times_number = models.IntegerField(
        blank=True, null=True)
    security_code_block_times_field = models.IntegerField(
        blank=True, null=True)
    max_security_code_tries = models.IntegerField(blank=True, null=True)
    # #

    def __unicode__(self):
        return self.name


class Card(models.Model):
    """
    Each Customer (User) may have one or more Cards, via which it is possible
    by an Operator to perform transactions (receiving or spending a currency).
    """
    card_type = models.ForeignKey('CardType', verbose_name=_('Card type'))
    number = models.OneToOneField(
        'CardNumber', verbose_name=_('Card number'), null=True)
    card_security_code = models.CharField(max_length=64, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    activation_date = models.DateTimeField(blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)
    card_security_code_blocked_until = models.DateTimeField(
        blank=True, null=True)
    owner = models.ForeignKey(
        'cyclos.User', verbose_name=_('Owner'), related_name='card_set')
    status = models.CharField(
        _('Status'), max_length=1, choices=CARD_STATUS_CHOICES,
        default=CARD_STATUS_ACTIVE)

    def __unicode__(self):
        try:
            if self.number:
                return u'{0} - {1}'.format(self.number, self.owner)
            else:
                return u'{0}'.format(self.owner)
        except CardNumber.DoesNotExist:
            return u'Card does not exist'

    def block_card(self):
        self.status = CARD_STATUS_BLOCKED
        self.save()

    def unblock_card(self):
        if self.status == CARD_STATUS_BLOCKED:
            self.status = CARD_STATUS_ACTIVE
            self.save()

    @property
    def is_active(self):
        return self.status == CARD_STATUS_ACTIVE

    class Meta:
        ordering = ('-creation_date', '-number', '-activation_date', 'owner')


#
# Terminal, Operator and Transaction models are not matched with Cyclos tables
#

class Terminal(models.Model):
    """
    A hardware device that allows logging in of Operators and is capable
    of communicating with Cards for performing transactions.
    """
    name = models.CharField(_('IMEI'), max_length=100, unique=True)
    business = models.ForeignKey(
        'cyclos.User', verbose_name=_('Business'), blank=True, null=True,
        related_name='terminal_set')
    icc_id = models.CharField(
        _('ICCID'), max_length=24, blank=True, validators=[iccid_validator, ])
    comments = models.TextField(_('Comments/Notes'), blank=True)
    creation_date = models.DateTimeField(_('Date created'), auto_now_add=True)
    last_seen_date = models.DateTimeField(
        _('Date last seen'), blank=True, null=True)
    removed_date = models.DateField(_('Date removed'), blank=True, null=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Override default save to do extra stuff

        - Update or create corresponding TerminalDeposits if business changes
        - Check/Update the quantity on SIM card and Terminal rental products
           for both businesses
        """
        old_business = None

        if self.id:
            # updating an existing Terminal object -- do nothing unless
            # business has changed
            old_terminal = Terminal.objects.get(pk=self.id)
            old_business = old_terminal.business
            business_changed = (old_business != self.business)
            if business_changed:
                # refund is due for this terminal, as long one as has been
                # charged previously (deposit_due is False)
                try:
                    td = TerminalDeposit.objects.get(
                        terminal=self, business=old_terminal.business)
                    if td.deposit_due:
                        # still waiting for a deposit, cancel it
                        td.deposit_due = False
                    else:
                        td.refund_due = True
                    td.save()
                except TerminalDeposit.DoesNotExist:
                    LOG.error(
                        "Terminal {0} was allocated to business {1}. "
                        "No matching TerminalDeposit found, so deposit "
                        "refund not generated.".format(
                            self.name, self.business)
                        )
        else:
            business_changed = True  # because it's a new Terminal object

        # now do the save (we need the id for the next step)
        super(Terminal, self).save(*args, **kwargs)

        if business_changed:
            # need to charge a deposit for this terminal if assigned
            # to a new business
            if self.business:
                td, created = TerminalDeposit.objects.get_or_create(
                    terminal=self, business=self.business,
                )
                if not created:
                    # TODO: any error conditions for existing TD?
                    td.deposit_due = True
                    td.save()

        # check/update the quantity on SIM card and Terminal rental
        # products for old and new businesses
        if business_changed:
            update_terminal_products(old_business)
        update_terminal_products(self.business)

    @property
    def business_name(self):
        if not self.business:
            return ''
        # get this way to avoid dying if multiple profiles for user
        # also getting the relative object was failing when images were missing
        cc3_profiles = CC3Profile.objects.filter(user=self.business,
                                                 user__is_active=True)\
            .values_list('business_name')
        try:
            cc3_profile = cc3_profiles[0]
        except Exception, e:
            print e
            return ''

        # business name is in tuple
        return cc3_profile[0]


class Operator(models.Model):
    """
    Each Operator may log in with their name and PIN at a Terminal, so long
    as it is linked with the same business.

    After logging in the Operator is allowed to perform transactions using
    Cards of customers.
    """
    name = models.CharField(_('Name'), max_length=255)
    business = models.ForeignKey(
        'cyclos.User', verbose_name=_('Business'), related_name='operator_set')
    pin = models.CharField(max_length=4)
    creation_date = models.DateTimeField(
        _('Creation Date'),auto_now_add=True)
    last_login_date = models.DateTimeField(
        _('Last Login Date'), blank=True, null=True)

    class Meta:
        unique_together = ('name', 'business')

    def __unicode__(self):
        return self.name


class CardTransaction(Transaction):
    """
    Subclasses core model ``core.Transaction``.

    Stores the details for each successful transaction executed via the card
    API.
    """
    operator = models.ForeignKey(
        'Operator', related_name='card_transaction_set',
        verbose_name=_('operator'))
    terminal = models.ForeignKey(
        'Terminal', related_name='card_transaction_set',
        verbose_name=_('terminal'))
    card = models.ForeignKey(
        'Card', related_name='card_transaction_set', verbose_name=_('card'))
    description = models.CharField(
        _('description'), max_length=255, blank=True)


class CardRegistration(models.Model):
    """
    New registrants can have old cards, new cards, not want a card or want to
    pick up the card in a shop.

    This model stores that choice, so that the register card view can be
    tailored according to registrants previous choices.
    """
    owner = models.ForeignKey(
        'cyclos.User', verbose_name=_('Owner'),
        related_name='card_registration_set')
    registration_choice = models.CharField(
        _('Registration Choice'), max_length=5,
        choices=CARD_REGISTRATION_CHOICES)
    creation_date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):

        reg_choice = self.registration_choice
        for choice in CARD_REGISTRATION_CHOICES:
            if choice[0] == reg_choice:
                # using cc3_profile here because get_profile() fails
                # for inactive users
                # (NB. no longer true. haven't changed the code though)
                return u'{0} ({1})'.format(choice[1], self.owner.cc3_profile)

    class Meta:
        ordering = ('-creation_date',)


class Fulfillment(models.Model):
    """
    Stores state of card order.
    """
    profile = models.ForeignKey(CC3Profile, verbose_name=_('Profile'))
    card_registration = models.ForeignKey(CardRegistration, null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    status = models.CharField(
        _('Status'), max_length=25, choices=CARD_FULFILLMENT_STATUSES
    )
    card = models.OneToOneField(
        'Card', verbose_name=_('Card'), null=True)

    class Meta:
        ordering = ('-status', '-last_modified',)
        verbose_name = _('Fulfillment')
        verbose_name_plural = _('Fulfillments')

    def cancel(self, status=CARD_FULLFILLMENT_CHOICE_ACCOUNT_CLOSED):
        self.status = status
        self.save()