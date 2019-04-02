# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def set_invoicing_company(apps, schema_editor):
    # set invoicing company in Product and Invoice,
    # so we can make it non-nullable
    Product = apps.get_model("billing", "Product")
    Invoice = apps.get_model("billing", "Invoice")
    InvoicingCompany = apps.get_model("billing", "InvoicingCompany")

    products = Product.objects.filter(invoiced_by__isnull=True)
    invoices = Invoice.objects.filter(invoicing_company__isnull=True)
    if invoices.count() or products.count():
        try:
            company = InvoicingCompany.objects.all()[0]
        except IndexError:
            company = InvoicingCompany.objects.create(
                company_name="Samen Doen BV")

    for product in products.all():
        product.invoiced_by = company
        product.save()
    for invoice in invoices.all():
        invoice.invoicing_company = company
        invoice.save()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0017_auto_20160718_1542'),
    ]

    operations = [
        migrations.RunPython(set_invoicing_company,
                             migrations.RunPython.noop),
    ]
