import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum, FloatField
from django.views.generic import (CreateView, DetailView, ListView,
                                  UpdateView)

from cc3.accounts.decorators import must_have_completed_profile
from cc3.billing.models import Product, AssignedProduct, Invoice
from cc3.cyclos.models import CC3Profile
from cc3.excelexport.views import CSVResponse


LOG = logging.getLogger(__name__)


class MyProductsListView(ListView):
    model = AssignedProduct
    template_name = 'accounts/products.html'

    def get_queryset(self):
        today = date.today()
        try:
            cc3_profile = self.request.user.cc3_profile
            qs = cc3_profile.assigned_products.exclude(
                start_date__gt=today).exclude(
                end_date__lt=today).exclude(
                quantity=0
            )
            return qs
        except CC3Profile.DoesNotExist:
            pass
        return AssignedProduct.objects.none()

    def get_context_data(self, **kwargs):
        context = super(MyProductsListView, self).get_context_data(**kwargs)

        try:
            cc3_profile = self.request.user.cc3_profile
            context['invoice_list'] = cc3_profile.invoices.order_by(
                '-invoice_date')
            # not much use, so leave them off
            #context['estimated_monthly_charges'] =   \
            #    cc3_profile.estimated_monthly_charges
            #context['estimated_yearly_charges'] =   \
            #    cc3_profile.estimated_yearly_charges
        except CC3Profile.DoesNotExist:
            pass

        context['is_billing_view'] = True

        return context


class MyProductsInvoiceView(DetailView):
    model = Invoice
    template_name = 'accounts/products_invoice.html'

    def get_context_data(self, **kwargs):
        context = super(MyProductsInvoiceView, self).get_context_data(**kwargs)

        context['is_billing_view'] = True
        context['invoice_list'] = Invoice.objects.filter(
            user_profile=self.request.user.cc3_profile)

        return context