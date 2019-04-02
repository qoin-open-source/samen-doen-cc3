# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0020_remove_assignedproduct_billing_frequency'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitem',
            name='discount_amount',
            field=models.DecimalField(default=0, help_text='This is a negative amount (or zero)', verbose_name='Discount (Euro)', max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='productpricing',
            name='type',
            field=models.CharField(default=b'UNIT', max_length=20, verbose_name='Price type', choices=[(b'UNIT', 'Unit price'), (b'TXN_UNIT', 'Per transaction charge'), (b'TXN_PERCENT', 'Transaction value percentage')]),
        ),
    ]
