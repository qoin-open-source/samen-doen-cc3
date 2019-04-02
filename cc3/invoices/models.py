# encoding: utf-8
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Max


VAT_RATE = getattr(settings, "VAT_RATE", 21)


class PaymentStatus(models.Model):
    description = models.CharField(max_length=255)
    is_active = models.BooleanField(blank=True)
    is_paid = models.BooleanField(blank=True)

    class Meta:
        ordering = ('description',)
        verbose_name_plural = 'payment statuses'

    def __unicode__(self):
        return self.description


class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=32)
    symbol = models.CharField(max_length=12)

    class Meta:
        ordering = ('code',)
        verbose_name_plural = 'currencies'

    def __unicode__(self):
        return self.name


class Invoice(models.Model):
    number = models.IntegerField(blank=True, unique=True)
    from_user = models.ForeignKey('cyclos.User', related_name='invoices_from')
    to_user = models.ForeignKey('cyclos.User', related_name='invoices_to')
    inv_date = models.DateField()
    due_date = models.DateField()
    currency = models.ForeignKey('invoices.Currency')
    payment_status = models.ForeignKey('invoices.PaymentStatus')

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    automatic_invoice = models.BooleanField(
        default=False,
        help_text=u'If this invoice was automatically generated')
    admin_comment = models.TextField(
        blank=True,
        help_text=u'Comment field for admin users, not shown to users')
    invoice_type = models.CharField(
        default='debit', choices=(('debit', 'Debit'), ('credit', 'Credit')),
        max_length=20)

    class Meta:
        ordering = ('number',)

    def __unicode__(self):
        return self.inv_no

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.get_next_invoice_number()
        return super(Invoice, self).save(*args, **kwargs)

    @property
    def inv_no(self):
        inv_no_prefix = getattr(settings, "INV_NO_PREFIX", 9999)
        return u"{0}{1:0{2}d}".format(
            inv_no_prefix, self.number, 5)

    def get_next_invoice_number(self):
        return (Invoice.objects.all().aggregate(
            Max('number'))['number__max'] or 0) + 1

    def get_sub_total(self):
        total = Decimal()
        for line in self.lines.all():
            total += line.net_total
        return total

    def get_tax(self):
        tax = Decimal()
        for line in self.lines.all():
            tax += line.get_tax()
        return tax

    def get_total(self):
        total = Decimal()
        for line in self.lines.all():
            total += line.grand_total
        return total

    def get_total_display(self):
        return "{0:.2f}".format(self.get_total())
    get_total_display.short_description = 'Total'


class InvoiceLine(models.Model):
    invoice = models.ForeignKey('invoices.Invoice', related_name='lines')
    description = models.CharField(max_length=255)
    quantity = models.IntegerField()
    amount = models.DecimalField(decimal_places=4, max_digits=12)
    tax_rate = models.DecimalField(
        decimal_places=4, max_digits=12, default=VAT_RATE)
    net_total = models.DecimalField(
        decimal_places=4, max_digits=12, blank=True)
    grand_total = models.DecimalField(
        decimal_places=4, max_digits=12, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('invoice__number', 'description',)

    def __unicode__(self):
        return u"{} {} at {} {}".format(
            self.quantity, self.description, self.amount,
            self.invoice.currency.code)

    def save(self, **kwargs):
        self.net_total = self._get_net_total()
        self.grand_total = self._get_grand_total()
        return super(InvoiceLine, self).save()

    def _get_net_total(self):
        return self.quantity * self.amount

    def get_tax(self):
        tax = Decimal()
        if self.tax_rate:
            net = self._get_net_total()
            tax = net * Decimal(str(self.tax_rate)) / Decimal(100)
        return tax

    def _get_grand_total(self):
        return self._get_net_total() + self.get_tax()
