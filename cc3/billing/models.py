# encoding: utf-8
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.core.validators import MaxValueValidator, MinLengthValidator
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

from cc3.core.models import SingletonModel
from cc3.cyclos import utils
from cc3.cyclos.models import CC3Profile, User

from .twinfield_exports import (
    get_products_xls, get_invoices_xls, get_users_xls
    )
from .common import (
    BILLING_PERIOD_YEARLY, BILLING_PERIOD_MONTHLY, BILLING_PERIOD_ONEOFF,
    BILLING_PERIODS, AUTO_ASSIGN_TYPES, AUTO_QTY_TYPES,
    AUTO_QTY_TYPE_TERMINALS_MINUS_ONE, AUTO_QTY_TYPE_TERMINALS,
    AUTO_QTY_TYPE_SIM_CARDS, AUTO_QTY_TYPE_TRANSACTION_VALUE,
    AUTO_QTY_TYPE_TRANSACTION_POINTS, AUTO_QTY_TYPE_TRANSACTION_COUNT,
    FILE_TYPE_TF_PRODUCTS, FILE_TYPE_TF_USERS, FILE_TYPE_TF_INVOICES,
    FILE_TYPE_TF_EXTRA_CSV, FILE_TYPES,
    load_dynamic_settings
    )


LOG = logging.getLogger(__name__)


CATEGORY_TYPE_SUBSCRIPTION = "SUBSCRIPTION"
CATEGORY_TYPE_TERMINALS_ETC = "TERMINALS"
CATEGORY_TYPE_TRANSACTIONS = "TRANSACTIONS"
CATEGORY_TYPE_OTHER = "OTHER"

CATEGORY_TYPES = (
    (CATEGORY_TYPE_SUBSCRIPTION, _('Subscriptions')),
    (CATEGORY_TYPE_TERMINALS_ETC, _('Cards and terminals')),
    (CATEGORY_TYPE_TRANSACTIONS, _('Transaction charges')),
    (CATEGORY_TYPE_OTHER, _('Other')),
)
DEFAULT_COST_CENTRE = 'TODO'


def apply_tax(amount, tax_percent):
    """Return amount + tax at tax_percent, as a Decimal"""
    if tax_percent:
        return Decimal(amount) * (
            Decimal(100.0) + Decimal(tax_percent)) / Decimal(100.0)
    return Decimal(amount)


def get_percent(amount, percent):
    """Return percent% of amount, as a Decimal"""
    if percent:
        return Decimal(amount) * Decimal(percent) / Decimal(100.0)
    return Decimal(0)


def get_discount(amount, discount_percent):
    """Return -(discount_percent% of amount), as a Decimal"""
    return -get_percent(amount, discount_percent)


class TaxRegime(models.Model):
    name = models.CharField(_('Name'), max_length=100)
    percent = models.DecimalField(
        _('% rate'), max_digits=5, decimal_places=2, blank=True, null=True)
    twinfield_code = models.CharField(
        _('2-letter Twinfield code'), max_length=2,
        validators=[MinLengthValidator(2)], default='??')

    def __unicode__(self):
        return self.name


class InvoicingCompany(models.Model):
    """
    Company that supplies Products / raises invoices
    """
    company_name = models.CharField(_('Name'), max_length=100)

    def __unicode__(self):
        return self.company_name


class Product(models.Model):
    """
    Defines a product that users can "buy"

    - subname, article_code, subarticle_code, cost_centre are all for
      TwinField use
    - user_groups -  Product can only be assigned to users in these groups

    """
    PRICE_TYPE_SIMPLE_UNIT_PRICE = "UNIT"
    PRICE_TYPE_PERCENTAGE = "PERCENTAGE"

    PRICE_TYPES = (
        (PRICE_TYPE_SIMPLE_UNIT_PRICE, _('Unit price')),
        (PRICE_TYPE_PERCENTAGE, _('Percentage of value')),
    )

    name = models.CharField(_('Name'), max_length=100)
    subname = models.CharField(
        _('Sub-name'), max_length=100, blank=True)
    article_code = models.CharField(
        _('Article code'), max_length=20)
    subarticle_code = models.CharField(
        _('Sub-article code'), max_length=20)
    category = models.CharField(
        _('Category'), max_length=20, choices=CATEGORY_TYPES,
        default=CATEGORY_TYPE_OTHER)
    cost_centre = models.CharField(
        _('Cost centre'), max_length=20, blank=True,
        default=DEFAULT_COST_CENTRE)
    user_groups = models.ManyToManyField(
        'cyclos.CyclosGroup', related_name='products',
        verbose_name=_('User groups'))
    price_type = models.CharField(
        _('Price type'), max_length=20, choices=PRICE_TYPES,
        default=PRICE_TYPE_SIMPLE_UNIT_PRICE)
    tax_regime = models.ForeignKey(
        TaxRegime, verbose_name=_('Tax regime'))
    max_discount_percent = models.IntegerField(
        _('Maximum discount (%)'), default=0,
        validators=[MaxValueValidator(100), ])
    min_qty = models.IntegerField(
        _('Minimum quantity'), default=0,
        help_text=_('Mimimum for Assigned Product quantity'))
    max_qty = models.IntegerField(
        _('Maximum quantity'), blank=True, null=True,
        help_text=_('Maximum for Assigned Product quantity '
                    '-- leave blank if no limit'))
    billing_frequency = models.CharField(
        _('Billing frequency'), max_length=12, choices=BILLING_PERIODS,
        default=BILLING_PERIOD_ONEOFF)
    auto_assign_type = models.CharField(
        _('Auto-assign type'), max_length=20, choices=AUTO_ASSIGN_TYPES,
        blank=True, help_text=_('Leave blank if assigned manually by admins'))
    auto_qty_type = models.CharField(
        _('Auto-quantity/value type'), max_length=20, choices=AUTO_QTY_TYPES,
        blank=True, help_text=_('Leave blank if set manually by admins'))
    invoiced_by = models.ForeignKey(
        InvoicingCompany, verbose_name=_('Invoicing company'),
        related_name='products')

    class Meta:
        unique_together = ("article_code", "subarticle_code")

    def __unicode__(self):
        return self.name

    @property
    def can_invoice_adhoc(self):
        # may want to make this independently settable in the future,
        # but for now...
        return self.billing_frequency == BILLING_PERIOD_ONEOFF

    @property
    def is_discountable(self):
        return self.max_discount_percent > 0

    @property
    def current_price(self):
        """Today's price, for display"""
        pricing = self.get_pricing_for_date(date.today())
        if pricing:
            return pricing.__unicode__()
        return _("No price set")

    @property
    def has_percentage_price(self):
        """Whether the pricing should be unit_price or percentage_price"""
        return self.price_type == self.PRICE_TYPE_PERCENTAGE

    def get_pricing_for_date(self, price_date):
        """
        Find the price of this product on price_date

        Find the ProductPricing where:
        - valid_from is <= price_date
        and
        - valid_to is None or >= price_date

        If no match found, log error and return None
        If more than one match found, log error and return the one with the
        latest start date
        """
        matches = self.prices.filter(
            valid_from__lte=price_date).exclude(valid_to__lt=price_date)
        if matches.count() == 1:
            return matches[0]
        if matches.count() > 1:
            LOG.warning(u"Multiple pricing found for '{0}' at {1}".format(
                self.name, price_date))
            return matches.order_by('-valid_from')[0]
        LOG.error(u"No pricing found for '{0}' at {1}".format(
            self.name, price_date))
        return None

    def get_todays_unit_price(self):
        todays_pricing = self.get_pricing_for_date(date.today())
        if todays_pricing is None:
            return 0.0
        return todays_pricing.get_unit_price()

    def is_valid_for_user(self, cc3_profile):
        """
        Check whether the user is allowed to have this product
        """
        return cc3_profile.cyclos_group in self.user_groups.all()

    def billing_period_as_string(self):
        pass

    def assign_to_user(self, cc3_profile):
        today = date.today()
        if cc3_profile.assigned_products.filter(
                product=self).exclude(
                start_date__gt=today).exclude(
                end_date__lt=today).count() == 0:
            ap = AssignedProduct(
                product=self, user_profile=cc3_profile, quantity=1)
            ap.save()
            LOG.info(u"Auto-assigned product: {0}".format(ap))

    def assign_to_user_groups(self):
        for group in self.user_groups.all():
            for cc3_profile in group.cc3profile_set.all():
                self.assign_to_user(cc3_profile)


class ProductPricing(models.Model):
    """
    Pricing info for a Product at a certain date

    A Product can have several associated ProductPricings, but their
    dates should not overlap. (A validation error is raised if attempting
    to save one that overlaps an existing one)
    """
    product = models.ForeignKey(
        Product, verbose_name=_('Product'), related_name=_('prices'))
    valid_from = models.DateField(_('Valid from'), default=date.today)
    valid_to = models.DateField(_('Valid to'), blank=True, null=True)
    unit_price_euros = models.DecimalField(
        _('Unit price (Euro)'), max_digits=10, decimal_places=2, default=0)
    percentage_price = models.DecimalField(
        _('Percentage price'), max_digits=5, decimal_places=2,
        blank=True, null=True)

    class Meta:
        ordering = ('-valid_from',)

    def __unicode__(self):
        if self.product.has_percentage_price:
            return u"{0}% of value".format(self.percentage_price)
        else:
            return u"€{0}".format(self.unit_price_euros)

    def get_unit_price(self):
        """Return unit_price if appropriate, otherwise 0"""
        if self.product.has_percentage_price:
            return 0
        else:
            return self.unit_price_euros

    def dates_overlap_with(self, product_pricing):
        """Checks whether valid_from and _to dates overlap with another PP"""
        if product_pricing.valid_to and (
                product_pricing.valid_to < self.valid_from):
            return False
        if self.valid_to and (
                self.valid_to < product_pricing.valid_from):
            return False
        return True

    def clean(self):
        """cross validate fields

        - If set, valid_to must be >= valid_from;
        - There must not be another ProductPricing for the same Product
          with overlapping dates
        """
        errors = []
        if self.valid_to and (self.valid_to < self.valid_from):
            errors.append(
                ugettext("'Valid from' cannot be before 'Valid to'"))

        for pp in self.product.prices.all():
            if pp != self and self.dates_overlap_with(pp):
                errors.append(ugettext(
                    "Valid-from and -to dates overlap an existing price"
                    ))

        if errors:
                raise ValidationError('; '.join(errors))


class AssignedProduct(models.Model):
    """Records that a user 'has' a product

    next_invoice_date defaults to start_date if no explicit value is supplied,
    and is updated automatically thereafter via the
    `generate_next_invoice_item` method.
    """
    product = models.ForeignKey(
        Product, related_name='assignments',
        verbose_name=_('Product'))
    user_profile = models.ForeignKey(
        'cyclos.CC3Profile', related_name='assigned_products',
        verbose_name=_('Assigned to user'))
    start_date = models.DateField(_('Start date'), default=date.today)
    end_date = models.DateField(_('End date'), blank=True, null=True)
    next_invoice_date = models.DateField(
        _('Date of next payment'), blank=True, null=True)
    quantity = models.IntegerField(
        _('Quantity'),
        help_text=_("Auto-calculated for rentals and subsciptions"))
    value = models.FloatField(
        _('Value'), blank=True, null=True,
        help_text=_("For percentage-based prices only"))
    discount_percent = models.IntegerField(
        _('Discount (%)'), default=0)

    class Meta:
        ordering = ('-next_invoice_date',)

    @property
    def billing_frequency(self):
        # Makes billing_frequency visible in AP admin;
        # also, if it turns out that we _do_ want to allow AP to have
        # different billing_frequency than its product, it can easily be
        # added into the model
        return self.product.billing_frequency

    @property
    def current_quantity(self):
        """Representation of 'quantity' for display purposes

        Needs to cope with auto-qty types that are totalled over a period
        """
        auto_qty_type = self.product.auto_qty_type
        if auto_qty_type in [AUTO_QTY_TYPE_TRANSACTION_VALUE,
                            AUTO_QTY_TYPE_TRANSACTION_POINTS,
                            AUTO_QTY_TYPE_TRANSACTION_COUNT]:
            # no 'current' quantity available
            # TODO 'month to date'?
            return ''
        if auto_qty_type:
            self.update_auto_quantity(save=True)
        return self.quantity

    def __unicode__(self):
        return u"{1}: {0}".format(
            self.product, self.user_profile.full_name)

    def clean(self):
        """cross validate fields

        - discount must be <= product.max_discount_percent;
        - user_profile must be in product.user_groups;
        - If set, end_date must be >= start_date;
        - If set, next_invoice_date must be >= start_date;
        - quantity must be >= product.min_qty;
        - quantity must be <= product.max_qty (if set);
        - There must not be another AP for the same Product
          with overlapping dates
        """
        errors = []
        if self.discount_percent > self.product.max_discount_percent:
            errors.append(
                ugettext("Max discount allowed for this product is {0}"
                         ).format(self.product.max_discount_percent)
                )
        if self.user_profile_id and self.product_id:
            if not self.product.is_valid_for_user(self.user_profile):
                errors.append(
                    ugettext("'{0}' is not available to users in group {1}"
                             ).format(self.product,
                                      self.user_profile.cyclos_group)
                    )
        if self.start_date:
            if self.end_date and (self.end_date < self.start_date):
                errors.append(
                    ugettext("End date cannot be before Start date"))
            if self.next_invoice_date and (
                    self.next_invoice_date < self.start_date):
                errors.append(
                    ugettext("Next Payment date cannot be before Start date"))

        if self.quantity < self.product.min_qty:
            errors.append(
                ugettext("Quantity should be >= {0}"
                         ).format(self.product.min_qty))
        if self.product.max_qty and (self.quantity > self.product.max_qty):
            errors.append(
                ugettext("Quantity should be <= {0}"
                         ).format(self.product.max_qty))

        if self.user_profile_id:
            for ap in self.user_profile.assigned_products.filter(
                        product=self.product):
                if ap != self and self.dates_overlap_with(ap):
                    errors.append(ugettext(
                        "This product is already assigned with overlapping dates"
                        ))

        if errors:
                raise ValidationError('; '.join(errors))

    def save(self, *args, **kwargs):
        """Override default save so we can populate some fields

        - Set next_invoice_date if unset on creation
        - Update auto-updated quantity
        """
        if not self.id:
            if not self.next_invoice_date:
                self.next_invoice_date = self.start_date
        self.update_auto_quantity(save=False)
        super(AssignedProduct, self).save(*args, **kwargs)

    def dates_overlap_with(self, assigned_product):
        """Checks whether start and end dates overlap with another AP"""
        if assigned_product.end_date and (
                assigned_product.end_date < self.start_date):
            return False
        if self.end_date and (assigned_product.start_date > self.end_date):
            return False
        return True

    def get_prices_for_date(self, price_date):
        """Get price and discount for this user and product at the given date

        Assumes the quantity and value fields are already correct
        """
        price_info = {}
        pricing = self.product.get_pricing_for_date(price_date)
        price_type = self.product.price_type
        # some prices are based on quantity, some on value
        qty = self.quantity
        if self.product.auto_qty_type in [AUTO_QTY_TYPE_TRANSACTION_VALUE, ]:
            qty = Decimal(self.value)
        if pricing:
            # calculate the price for this user
            if price_type == Product.PRICE_TYPE_SIMPLE_UNIT_PRICE:
                unit_price = pricing.unit_price_euros
                quantity = qty
                total_price = pricing.unit_price_euros * quantity
            elif price_type == Product.PRICE_TYPE_PERCENTAGE:
                unit_price = get_percent(qty, pricing.percentage_price)
                quantity = self.quantity
                total_price = unit_price * quantity
            else:
                raise NotImplementedError

            tax_percent = pricing.product.tax_regime.percent
            discount = get_discount(total_price, self.discount_percent)

            price_info = {
                'unit_price_ex_tax': unit_price,
                'unit_price_incl_tax': apply_tax(unit_price, tax_percent),
                'total_price_ex_tax': total_price,
                'total_price_incl_tax': apply_tax(total_price, tax_percent),
                'discount_amount_ex_tax': discount,
                'discount_amount_incl_tax': apply_tax(discount, tax_percent),
                'quantity': quantity,
                'price_type': price_type,
            }
        return price_info

    def generate_next_invoice_item(self, invoice):
        """Create an InvoiceItem for the next_invoice_date

        Also update the next_invoice_date
        """
        invoice_item = None
        price_info = self.get_prices_for_date(self.next_invoice_date)

        if price_info:
            if price_info.get('quantity', 0):
                # don't create invoice line if quantity is zero
                invoice_item = InvoiceItem.objects.create(
                    assigned_product=self,
                    invoice=invoice,
                    payment_for_date=self.next_invoice_date,
                    quantity=price_info['quantity'],
                    unit_price_ex_tax=price_info['unit_price_ex_tax'],
                    unit_price_incl_tax=price_info['unit_price_incl_tax'],
                    discount_amount_ex_tax=price_info[
                        'discount_amount_ex_tax'],
                    discount_amount_incl_tax=price_info[
                        'discount_amount_incl_tax'],
                    tax_percent=self.product.tax_regime.percent,
                    tax_name=self.product.tax_regime.name,
                )
            self.update_next_invoice_date()
        else:
            msg = u"Failed to raise invoice for '{0}' (no price found)".format(
                self.__unicode__())
            LOG.error(msg)
            raise RuntimeError(msg)
        return invoice_item

    def update_next_invoice_date(self):
        """Update next_invoice_date according to billing frequency"""
        freq = self.billing_frequency
        if freq == BILLING_PERIOD_ONEOFF:
            self.next_invoice_date = None
        elif freq == BILLING_PERIOD_MONTHLY:
            self.next_invoice_date += relativedelta(months=+1)
        elif freq == BILLING_PERIOD_YEARLY:
            self.next_invoice_date += relativedelta(years=+1)
        # don't ask for payment past the end_date
        if self.end_date and self.next_invoice_date and (
                self.next_invoice_date > self.end_date):
            self.next_invoice_date = None
        self.save()

    def update_auto_quantity(self,
                             period_start=None, period_end=None, save=False):
        if self.product.auto_qty_type == AUTO_QTY_TYPE_TERMINALS:
            self.quantity = self.user_profile.user.terminal_set.filter(
                removed_date__isnull=True).count()
            if save:
                self.save()

        elif self.product.auto_qty_type == AUTO_QTY_TYPE_TERMINALS_MINUS_ONE:
            self.quantity = max(0, self.user_profile.user.terminal_set.filter(
                removed_date__isnull=True).count() - 1)
            if save:
                self.save()

        elif self.product.auto_qty_type == AUTO_QTY_TYPE_SIM_CARDS:
            self.quantity = self.user_profile.user.terminal_set.filter(
                removed_date__isnull=True).exclude(icc_id='').count()
            if save:
                self.save()

        elif self.product.auto_qty_type in [AUTO_QTY_TYPE_TRANSACTION_VALUE,
                                            AUTO_QTY_TYPE_TRANSACTION_POINTS,
                                            AUTO_QTY_TYPE_TRANSACTION_COUNT]:
            # only update these if period start and end dates are supplied
            if period_start and period_end:
                total_txns, total_points =   \
                    self.product.transaction_params.get_transaction_totals(
                        self.user_profile.user.username,
                        period_start, period_end)

                self.quantity = 0
                self.value = 0

                if (self.product.auto_qty_type ==
                        AUTO_QTY_TYPE_TRANSACTION_VALUE and total_points):
                    self.quantity = 1
                    self.value = float(
                        total_points) / settings.CC3_CURRENCY_CONVERSION
                elif (self.product.auto_qty_type ==
                        AUTO_QTY_TYPE_TRANSACTION_POINTS and total_points):
                    self.quantity = int(total_points)
                elif (self.product.auto_qty_type ==
                        AUTO_QTY_TYPE_TRANSACTION_COUNT) and total_txns:
                    self.quantity = total_txns

                if save:
                    self.save()


class InvoiceSet(models.Model):
    """Represents a set of invoices generated and exported at the same time

    Records the generation of csv files and their export to TwinField
    """
    description = models.TextField(_('Description'), blank=True)
    period_start = models.DateField(
        _('Period start date'), blank=True, null=True,
        help_text=_("Blank for ad-hoc invoices"))
    period_end = models.DateField(
        _('Period end date'), blank=True, null=True,
        help_text=_("Blank for ad-hoc invoices"))
    invoices_created_at = models.DateTimeField(
        _('Invoices created at'), null=True, blank=True)
    generated_at = models.DateTimeField(
        _('Files generated at'), null=True, blank=True)
    sent_at = models.DateTimeField(
        _('Files sent at'), null=True, blank=True)
    sent_to = models.TextField(_('Files sent to'), blank=True)

    def generate_twinfield_files(self,
                                 include_headings=True,
                                 replace_existing_files=True,
                                 encoding='utf-8'):
        if replace_existing_files:
            existing_files = self.data_files.exclude(
                file_type=FILE_TYPE_TF_EXTRA_CSV)
            # first delete the underlying files
            for f in existing_files.all():
                if f.data_file:
                    f.data_file.delete()
            # then the objects themselves
            existing_files.delete()

        invoicing_companies = set(
            [i.invoicing_company for i in self.invoices.all()])

        for invoicing_company in invoicing_companies:
            # need a separate items file for each company
            items_xls = get_invoices_xls(
                self.invoices.filter(invoicing_company=invoicing_company),
                include_headings, encoding)
            invoices_file = InvoiceDataFile(
                file_type=FILE_TYPE_TF_INVOICES,
                invoice_set=self)
            slug = invoicing_company.company_name.replace(' ', '')
            invoices_file.save_file(items_xls.getvalue(), extra_slug=slug)

        invoice_items_qs = InvoiceItem.objects.filter(
            invoice__in=self.invoices.all())

        product_ids = invoice_items_qs.values_list(
            'assigned_product__product', flat=True).distinct()
        product_queryset = Product.objects.filter(id__in=product_ids)
        products_xls = get_products_xls(
            product_queryset, include_headings, encoding)
        products_file = InvoiceDataFile(
            file_type=FILE_TYPE_TF_PRODUCTS,
            invoice_set=self)
        products_file.save_file(products_xls.getvalue())

        profile_ids = invoice_items_qs.values_list(
            'assigned_product__user_profile', flat=True).distinct()
        profile_queryset = CC3Profile.objects.filter(id__in=profile_ids)
        users_xls = get_users_xls(
            profile_queryset, include_headings)
        users_file = InvoiceDataFile(
            file_type=FILE_TYPE_TF_USERS,
            invoice_set=self)
        users_file.save_file(users_xls.getvalue())

        self.generated_at = datetime.now()
        self.save()

    def send_twinfield_files(self):
        """Send the TF files to the configured address(es)"""
        if not self.data_files.count():
            LOG.info("Not sending Twinfield files -- invoice set has no files")
            return False

        dyn_settings = load_dynamic_settings()
        to_list = [addr.strip() for addr in
                   dyn_settings.TWINFIELD_EMAIL_FILES_TO.split(',')]
        if not to_list:
            LOG.info("Not sending Twinfield files -- no address configured")
            return False

        msg = EmailMessage(
            subject=self.description,
            body=self.description,
            to=to_list,
        )
        for f in self.data_files.all():
            msg.attach_file(f.full_file_path)
        msg.send()

        self.sent_at = datetime.now()
        self.save()
        return True


class Invoice(models.Model):
    """Typically a monthly invoice, but also an ad-hoc invoice"""
    invoice_set = models.ForeignKey(
        InvoiceSet, related_name='invoices', verbose_name=_('Invoice set'))
    invoice_date = models.DateField(_('Invoice date'))
    user_profile = models.ForeignKey(
        'cyclos.CC3Profile', related_name='invoices',
        verbose_name=_('User profile'))
    description = models.TextField(_('Description'), blank=True)
    date_exported = models.DateField(
        _('Date exported to TwinField'), blank=True, null=True)
    invoicing_company = models.ForeignKey(
        InvoicingCompany, verbose_name=_('Invoicing company'),
        related_name='invoices')

    def __unicode__(self):
        return self.description

    @property
    def invoice_total_ex_tax(self):
        return (
            self.items.aggregate(result_value=models.Sum(
                models.F('unit_price_ex_tax') * models.F('quantity'),
                output_field=models.FloatField())).get('result_value', 0.00)
            +
            self.items.aggregate(result_value=models.Sum(
                models.F('discount_amount_ex_tax'),
                output_field=models.FloatField())).get('result_value', 0.00)
            )

    @property
    def invoice_total_incl_tax(self):
        return (
            self.items.aggregate(result_value=models.Sum(
                models.F('unit_price_incl_tax') * models.F('quantity'),
                output_field=models.FloatField())).get('result_value', 0.00)
            +
            self.items.aggregate(result_value=models.Sum(
                models.F('discount_amount_incl_tax'),
                output_field=models.FloatField())).get('result_value', 0.00)
            )


class InvoiceItem(models.Model):
    """Represents an item on an invoice

    Used for 2 purposes:
    1. To generate the data file for TwinField
    2. As a snapshot which can be used to show the user what we believe they
       have been invoiced for. (In the future we may want to get this info
       directly from TwinField)

    Because of #2 it contains copies of pricing and tax info not strictly
    needed for #1
    """

    assigned_product = models.ForeignKey(
        AssignedProduct, verbose_name=_('Assigned product'))
    invoice = models.ForeignKey(
        Invoice, related_name='items', verbose_name=_('Invoice'))
    payment_for_date = models.DateField(_('Date payment is for'))
    quantity = models.IntegerField(_('Quantity'))
    unit_price_ex_tax = models.DecimalField(
        _('Unit price excl. tax (Euro)'), max_digits=10, decimal_places=2)

    discount_amount_ex_tax = models.DecimalField(
        _('Discount excl. tax (Euro)'),
        max_digits=10, decimal_places=2, default=0,
        help_text=_('This is a negative amount (or zero)'))
    # following fields are all snapshot fields for #2 but not used in
    # TwinField export
    unit_price_incl_tax = models.DecimalField(
        _('Unit price incl. tax (Euro)'), max_digits=10, decimal_places=2)
    discount_amount_incl_tax = models.DecimalField(
        _('Discount incl. tax (Euro)'),
        max_digits=10, decimal_places=2, default=0,
        help_text=_('This is a negative amount (or zero)'))
    tax_name = models.CharField(_('Name'), max_length=100)
    tax_percent = models.DecimalField(
        _('% rate'), max_digits=5, decimal_places=2, blank=True, null=True)

    @property
    def line_total_ex_tax(self):
        return self.quantity * self.unit_price_ex_tax

    @property
    def line_total_incl_tax(self):
        return self.quantity * self.unit_price_incl_tax

    @property
    def discount_description(self):
        return _("Discount on '{0}' at {1}%").format(
            self.assigned_product.product,
            self.assigned_product.discount_percent)


class InvoiceDataFile(models.Model):
    """One of the Twinfield files (articles, debtors, invoices)"""
    invoice_set = models.ForeignKey(
        InvoiceSet, related_name='data_files', verbose_name=_('Invoice set'))
    file_type = models.CharField(
        _('File type'), max_length=10, choices=FILE_TYPES,
        default=FILE_TYPE_TF_INVOICES)
    generated_at = models.DateTimeField(null=True, blank=True)
    data_file = models.FileField(upload_to='billing/%Y/')

    def __unicode__(self):
        return self.data_file.name

    def save_file(self, contents, extra_slug=''):
        self.generated_at = datetime.now()
        self.data_file.save(
            self.twinfield_filename(extra_slug), ContentFile(contents))

    def twinfield_filename(self, extra_slug):
        if self.file_type == FILE_TYPE_TF_EXTRA_CSV:
            extension = 'csv'
        else:
            extension = 'xls'
        if extra_slug:
            template = "{name}_{extra}_{datestamp}_{id:06d}.{extension}"
        else:
            template = "{name}_{datestamp}_{id:06d}.{extension}"

        return template.format(
            datestamp=datetime.date(self.generated_at).isoformat(),
            name=self.file_type,
            id=self.invoice_set.id,
            extension=extension,
            extra=extra_slug,
        )

    @property
    def full_file_path(self):
        if self.data_file:
            return os.path.join(settings.MEDIA_ROOT, self.data_file.name)
        return ''


class TerminalDeposit(models.Model):
    """Keeps track of deposits and refunds on cards.models.Terminals

    (Can't just add these fields to Terminal because they get re-assigned to
    other users)

    These are created and updated in Terminal.save()

    An initial migration will create TerminalDeposits for all existing
    Terminals, with deposit_due=False
    """
    business = models.ForeignKey(
        'cyclos.User', verbose_name=_('Business'))
    terminal = models.ForeignKey(
        'cards.Terminal', verbose_name=_('Terminal'))
    deposit_due = models.BooleanField(default=True)
    refund_due = models.BooleanField(default=False)
    date_deposit_charged = models.DateTimeField(null=True, blank=True)
    date_deposit_refunded = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("business", "terminal")

    def record_deposit_charged(self, date_charged=None):
        if not date_charged:
            date_charged = date.today()
        self.deposit_due = False
        self.date_deposit_charged = date_charged
        self.save()

    def record_deposit_refunded(self, date_refunded=None):
        if not date_refunded:
            date_refunded = date.today()
        self.refund_due = False
        self.date_deposit_refunded = date_refunded
        self.save()


class BillingSettings(SingletonModel):
    """
    Single record allowing admins to update settings
    """
    TWINFIELD_PROJECT_CODE = models.CharField(
        _('Twinfield Project Code'), max_length=20, default='P0001')
    TWINFIELD_GL_ACCOUNT_PRODUCTS = models.CharField(
        _('Twinfield GL account for Products'), max_length=20, default='8000')
    TWINFIELD_GL_ACCOUNT_USERS = models.CharField(
        _('Twinfield GL account for Users'), max_length=20, default='1300')
    TWINFIELD_CREDIT_MANAGER = models.CharField(
        _('Twinfield credit manager'), max_length=20, default='QOIN2')
    TWINFIELD_USER_CODE_TEMPLATE = models.CharField(
        _('Twinfield user code template'), max_length=20, default='SD{0:06d}')
    TWINFIELD_INVOICE_TYPE = models.CharField(
        _('Twinfield invoice type'), max_length=20, default='01')
    TWINFIELD_EMAIL_FILES_TO = models.CharField(
        _('Mail Twinfield data files to'),
        max_length=200, blank=True, default='',
        help_text=_('Email address(es), comma separated if more than one'))

    class Meta:
        verbose_name_plural = "Billing Settings"


class TransactionParams(models.Model):
    """
    Defines a transaction for use by a transaction-type Product

    - Cyclos groups of sender and recipient
    - transaction type ID
    - whether the sender or the recipient is to be invoiced
    - whether the transactions amounts need to be negated for the total
      (will need to do this if the cyclos transaction amounts are negative)
    """
    sender_group = models.ForeignKey(
        'cyclos.CyclosGroup', verbose_name=_('Sender group'),
        related_name='uniq1', blank=True, null=True)
    recipient_group = models.ForeignKey(
        'cyclos.CyclosGroup', verbose_name=_('Receiver group'),
        related_name='uniq2', blank=True, null=True)
    txn_type_id = models.IntegerField(_('Transaction Type ID'))
    invoice_sender = models.BooleanField(_('Invoice sender?'))
    invoice_recipient = models.BooleanField(_('Invoice recipient?'))
    negate_amounts = models.BooleanField(
        _('Negate transaction amounts?'), default=False)
    product = models.OneToOneField(
        Product, related_name='transaction_params')

    class Meta:
        verbose_name_plural = "Transaction parameters"

    def _get_user_from_username(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    def get_transaction_totals(self, username, from_date, to_date):
        """
        Total up matching transactions by user between the two dates
        (which are inclusive)

        Return total number of transactions, and total number of points
        """
        conn = utils.get_cyclos_connection()
        senders = None
        recipients = None
        if self.invoice_sender:
            senders = [username, ]
        if self.invoice_recipient:
            recipients = [username, ]

        txns = utils.get_cyclos_transfers(
            conn, senders=senders, recipients=recipients,
            transfer_type_ids=[self.txn_type_id, ],
            from_date=from_date, to_date=to_date)

        # txns is a list; further filtering needed
        total = 0
        count = 0
        exclude_desc = getattr(settings,
                               'BILLING_EXCLUDE_TRANSFERS_CONTAINING', "")
        for txn in txns:
            # exclude non-charged transactions
            if exclude_desc and (exclude_desc in txn['description']):
                continue
            if self.sender_group:
                sender_user = self._get_user_from_username(txn['sender'])
                if not sender_user or (
                        sender_user.get_profile().cyclos_group !=
                        self.sender_group):
                    continue
            if self.recipient_group:
                recipient_user = self._get_user_from_username(txn['recipient'])
                if not recipient_user or (
                        recipient_user.get_profile().cyclos_group !=
                        self.recipient_group):
                    continue
            # valid transaction -- add it to total and count
            total += txn['amount']
            count += 1

        utils.close_cyclos_connection(conn)

        if self.negate_amounts:
            return count, -total
        else:
            return count, total
