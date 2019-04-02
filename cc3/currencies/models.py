# encoding: utf-8
""" Currency related models. """
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Currency(models.Model):

    """ Model to hold information about a currency.

    A user can hold an account if it is marked as 'can_be_primary'

    """

    iso_code = models.CharField(
        _('ISO code'),
        max_length=3,
        validators=[MinLengthValidator(3)],
        help_text=_('ISO 4217 code, e.g. GBP, if one exists'),
        blank=True,
        default='')
    symbol = models.CharField(
        max_length=16, help_text='e.g. £')
    name = models.CharField(
        max_length=64, help_text='e.g. British Pound')
    cyclos_symbol = models.CharField(
        max_length=16, blank=True, default='',
        help_text=_("Symbol for currency in cyclos if available, "
                    "for web service access."))
    can_be_primary = models.BooleanField(
        default=True,
        help_text=_("Is currency available to users as a primary currency?"))

    class Meta:
        ordering = ('iso_code',)
        verbose_name_plural = _('currencies')
        unique_together = ('symbol', 'iso_code', 'cyclos_symbol')

    def __unicode__(self):
        """ currency identified by iso_code. """
        return u"%s" % self.symbol


class CurrencyPair(models.Model):

    """ Model for currency pairs, and the last obtained indicative quote rate.

    The rate is updated regularly by a background process, via the FIX link
    with DealHub (we could add a flag whether this update is to be active
        or not)

    Also need to test whether the CurrencyPair is valid with DealHub
    [ for example USD/JPY is valid, JPY/USD is not ]
    """

    base = models.ForeignKey(Currency, related_name="base_currency")
    counter = models.ForeignKey(Currency, related_name="counter_currency")
    # TODO Could be programmatically generated?
    symbol = models.CharField(max_length=16, help_text="e.g. EUR/USD.")
    last_updated = models.DateTimeField(auto_now=True)
    rate = models.DecimalField(default=0, max_digits=8, decimal_places=2)

    # TODO add a flag to say whether the indicative quote for the pair should
    #  beupdated regularly via FIX. NB could be an 'active' type flag

    def __unicode__(self):
        """ symbol, base iso_code, counter iso_code. """
        return u"%s (%s/%s)" % (
            self.symbol,
            self.base.iso_code,
            self.counter.iso_code
        )
