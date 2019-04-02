# encoding: utf-8
from django.http import HttpResponse
from django.views.generic import ListView
from django.views.generic.detail import BaseDetailView
from django.http import Http404

from .models import Invoice
from .utils import generate_invoice_excel, generate_invoice_pdf


class InvoiceListView(ListView):
    model = Invoice
    paginate_by = 10

    def get_queryset(self):
        return Invoice.objects.filter(to_user=self.request.user)


class InvoicePermissionMixin(object):
    """
    Restrict access to users who received/sent the invoice and
    (community) admins.
    Raise a 404 for all other users
    """
    def check_permission(self, request, *args, **kwargs):
        invoice = self.get_object()
        if request.user not in [invoice.from_user, invoice.to_user] and \
                request.user.is_staff is False and \
                not request.user.is_community_admin():
            raise Http404
        return


class InvoiceExcelView(InvoicePermissionMixin, BaseDetailView):
    model = Invoice

    def _get_filename(self):
        return self.get_object().inv_no

    def get(self, request, *args, **kwargs):
        self.check_permission(request)
        self.object = self.get_object()
        resp = HttpResponse(content_type='application/vnd.ms-excel')
        resp.content = generate_invoice_excel(self.object)
        resp['Content-Disposition'] = u'attachment;filename="{}.xls"'.format(
            self._get_filename())
        return resp


class InvoicePDFView(InvoicePermissionMixin, BaseDetailView):
    model = Invoice

    def _get_filename(self):
        return self.get_object().inv_no

    def get(self, request, *args, **kwargs):
        self.check_permission(request)
        self.object = self.get_object()
        resp = HttpResponse(content_type='application/pdf')
        resp.content = generate_invoice_pdf(self.object)
        resp['Content-Disposition'] = u'attachment; filename="{}.pdf"'.format(
            self._get_filename())
        return resp
