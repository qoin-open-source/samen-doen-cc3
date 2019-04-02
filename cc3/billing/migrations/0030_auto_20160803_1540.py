# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def delete_orphaned_invoices(apps, schema_editor):
    # Delete all invoices with no invoice_set (so we can make it non-nullable)
    Invoice = apps.get_model("billing", "Invoice")
    Invoice.objects.exclude(invoice_set__isnull=False).delete()
    # and delete all invoice sets with no invoices
    InvoiceSet = apps.get_model("billing", "InvoiceSet")
    InvoiceSet.objects.filter(invoices__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0029_auto_20160803_1537'),
    ]

    operations = [
        migrations.RunPython(delete_orphaned_invoices,
                             reverse_code=migrations.RunPython.noop),
    ]
