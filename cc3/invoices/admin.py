# encoding: utf-8
from django.contrib import admin
from django.core.urlresolvers import reverse

from cc3.excelexport.admin import admin_action_export_xls

from .models import Currency, Invoice, InvoiceLine, PaymentStatus


class CurrencyAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('code', 'name', 'symbol',)
    search_fields = ('code', 'name',)


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine


class InvoiceAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    inlines = [InvoiceLineInline]
    list_display = (
        'inv_no', #'from_user', 'to_user',
        'invoice_type', 'inv_date', 'due_date',
        'payment_status', 'get_total_display', 'currency',
        'export_invoice'
    )
    list_filter = ('payment_status', 'invoice_type')
    readonly_fields = ('number', 'created')

    def export_invoice(self, obj):
        """ Allow downloading of the PDF via the admin """
        return u"[<a href='{0}'>PDF</a>]".format(
            reverse('invoice_download_pdf', args=[obj.id]), reverse('invoice_download_excel', args=[obj.id]))
    export_invoice.allow_tags = True


class PaymentStatusAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('description', 'is_active', 'is_paid',)
    list_filter = ('is_active', 'is_paid',)

# Invoices app becoming obsolete -- remove links from django admin
#
#admin.site.register(Invoice, InvoiceAdmin)
#admin.site.register(PaymentStatus, PaymentStatusAdmin)
#admin.site.register(Currency, CurrencyAdmin)
