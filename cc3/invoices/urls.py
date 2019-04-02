# encoding: utf-8
from django.conf.urls import *
from django.contrib.auth.decorators import login_required

from .views import InvoiceListView, InvoiceExcelView, InvoicePDFView


urlpatterns = patterns('',
    url(
        regex=r'^invoices/invoice/list/$',
        view=login_required(InvoiceListView.as_view()),
        name='invoice_list'
    ),
    url(
        regex=r'^invoices/invoice/(?P<pk>\d+)/download/excel/$',
        view=login_required(InvoiceExcelView.as_view()),
        name='invoice_download_excel'
    ),
    url(
        regex=r'^invoices/invoice/(?P<pk>\d+)/download/pdf/$',
        view=login_required(InvoicePDFView.as_view()),
        name='invoice_download_pdf'
    )
)
