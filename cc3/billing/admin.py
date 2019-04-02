from datetime import date

from django.contrib import admin, messages
from django.utils.translation import ugettext as _

from .common import MONTHLY_EXTRA_TWINFIELD_FILES
from .models import (
    Product, ProductPricing, AssignedProduct, TaxRegime,
    InvoiceItem, Invoice, InvoicingCompany, InvoiceDataFile, InvoiceSet,
    TerminalDeposit, BillingSettings, TransactionParams
    )
from .utils import generate_adhoc_invoices


@admin.register(ProductPricing)
class ProductPricingAdmin(admin.ModelAdmin):
    list_filter = [
        'product', 'product__price_type',
    ]
    list_display = [
        'product', 'unit_price_euros', 'percentage_price',
        'valid_from', 'valid_to',
        ]


class ProductPricingInline(admin.TabularInline):
    model = ProductPricing


class TransactionParamsInline(admin.StackedInline):
    model = TransactionParams


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    def assign_to_user_groups(self, request, queryset):
        for p in queryset.all():
            p.assign_to_user_groups()
    assign_to_user_groups.short_description = _(
        u"Assign selected Product(s) to all users in its user groups")

    list_display = [
        'name', 'category', 'tax_regime', 'current_price',
        'max_discount_percent', 'billing_frequency', 'invoiced_by'
    ]
    list_filter = [
        'category', 'tax_regime', 'billing_frequency', 'invoiced_by',
    ]
    filter_horizontal = [
        'user_groups',
    ]
    inlines = [
        ProductPricingInline, TransactionParamsInline,
    ]
    actions = [assign_to_user_groups,]


class InvoiceItemAdmin(admin.TabularInline):
    model = InvoiceItem
    readonly_fields = (
        'assigned_product', 'payment_for_date', 'quantity',
        'unit_price_ex_tax',
    )
    can_delete = False
    max_num = 0


@admin.register(AssignedProduct)
class AssignedProductAdmin(admin.ModelAdmin):

    def business_name(self, obj):
        # so we can show business name in changelist
        return obj.user_profile.business_name

    def _generate_and_send_invoices(self, request, queryset, send):
        invoices, items, errors = generate_adhoc_invoices(
            assigned_products_qs=queryset,
            invoice_date=date.today(),
            send_to_twinfield=send)
        for msg in errors:
            messages.error(request, msg)
        items_expected = queryset.count()
        message = _(
            u'Invoiced {0} of {1} items; Created {2} invoices'.format(
                items, items_expected, invoices)
            )
        if items_expected == items:
            messages.success(request, message)
        else:
            messages.warning(request, message)

    def generate_and_send_invoices(self, request, queryset):
        self._generate_and_send_invoices(request, queryset, send=True)
    generate_and_send_invoices.short_description = _(
        u"Generate and send ad-hoc invoice(s) for selected items")

    def generate_invoices(self, request, queryset):
        self._generate_and_send_invoices(request, queryset, send=False)
    generate_invoices.short_description = _(
        u"Generate ad-hoc invoice(s) for selected items")

    def testing_reset_dates(self, request, queryset):
        from datetime import date
        queryset.update(next_invoice_date=date(day=15, month=9, year=2016))
    testing_reset_dates.short_description = _(
        u"TESTING ONLY: reset next payment date to 15-Sept-2016")

    list_display = [
        'product', 'business_name',
        'quantity', 'discount_percent', 'billing_frequency',
        'next_invoice_date', 'start_date', 'end_date',
    ]
    list_filter = [
        'product', 'product__billing_frequency',
    ]
    search_fields = (
        'user_profile__first_name',
        'user_profile__last_name',
        'user_profile__user__email',
        'user_profile__user__first_name',
        'user_profile__user__last_name',
        'user_profile__business_name',
    )
    raw_id_fields = ['user_profile']
    actions = [generate_invoices, generate_and_send_invoices,
               testing_reset_dates]


@admin.register(TaxRegime)
class TaxRegimeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'percent', 'twinfield_code',
    ]


@admin.register(InvoicingCompany)
class InvoicingCompanyAdmin(admin.ModelAdmin):
    pass


@admin.register(TerminalDeposit)
class TerminalDepositAdmin(admin.ModelAdmin):
    list_display = ['terminal', 'business', 'deposit_due', 'refund_due']


class InvoiceDataFileInline(admin.TabularInline):
    model = InvoiceDataFile
    fields = (
        'data_file', 'file_type',
    )
    readonly_fields = (
        'data_file', 'file_type',
    )
    can_delete = False
    max_num = 0


class InvoiceInline(admin.TabularInline):
    model = Invoice
    fields = (
        'user_profile', 'invoice_date', 'invoicing_company', 'description',
    )
    readonly_fields = (
        'user_profile', 'invoice_date', 'invoicing_company', 'description',
    )
    can_delete = False
    max_num = 0


@admin.register(InvoiceSet)
class InvoiceSetAdmin(admin.ModelAdmin):

    def generate_tf_files(self, request, queryset):
        for invoice_set in queryset.all():
            invoice_set.generate_twinfield_files()
        messages.success(request,_("Files generated"))
    generate_tf_files.short_description = _(
        u"(Re-)Generate Twinfield files")

    #def generate_extra_tf_files(self, request, queryset):
    #    for invoice_set in queryset.all():
    #        invoice_set.generate_extra_twinfield_files(
    #            MONTHLY_EXTRA_TWINFIELD_FILES)
    #    messages.success(request, _("Files generated"))
    #generate_extra_tf_files.short_description = _(
    #    u"(Re-)Generate Extra Twinfield files")

    def send_tf_files(self, request, queryset):
        for invoice_set in queryset.all():
            invoice_set.send_twinfield_files()
        messages.success(request,
            _("Files sent"))
    send_tf_files.short_description = _(u"(Re-)Send Twinfield files")

    inlines = [InvoiceDataFileInline, InvoiceInline, ]
    list_display = ['description', 'period_start', 'period_end',
                    'invoices_created_at', 'generated_at', 'sent_at', ]
    exclude = ['invoices', ]  # done by inline instead
    #actions = [generate_tf_files, generate_extra_tf_files, send_tf_files, ]
    actions = [generate_tf_files, send_tf_files, ]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    inlines = [
        InvoiceItemAdmin,
    ]
    list_display = [
        'description', 'invoicing_company', 'user_profile',
        'invoice_date', 'date_exported',
        ]
    raw_id_fields = ['user_profile', ]


@admin.register(BillingSettings)
class BillingSettingsAdmin(admin.ModelAdmin):
    pass
