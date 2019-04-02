# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def set_assigned_product_billing_frequency(apps, schema_editor):
    # just run through saving them all, updating billing_frequency from the product
    AssignedProduct = apps.get_model("billing", "AssignedProduct")
    for ap in AssignedProduct.objects.all():
        ap.billing_frequency = ap.product.billing_frequency
        ap.save()

class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0016_assignedproduct_billing_frequency'),
    ]

    operations = [
        migrations.RunPython(set_assigned_product_billing_frequency,
                             migrations.RunPython.noop),
    ]
