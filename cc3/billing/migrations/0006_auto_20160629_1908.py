# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0005_auto_20160629_1831'),
    ]

    operations = [
        migrations.RenameField(
            model_name='assignedproduct',
            old_name='discount',
            new_name='discount_percent',
        ),
        migrations.RemoveField(
            model_name='productpayment',
            name='payment_amount_euros',
        ),
        migrations.AddField(
            model_name='productpayment',
            name='discounted_price_euros',
            field=models.DecimalField(default=0, verbose_name='Discounted price (Euro)', max_digits=10, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productpayment',
            name='tax_amount_euros',
            field=models.DecimalField(default=0, verbose_name='Tax amount (Euro)', max_digits=10, decimal_places=2),
            preserve_default=False,
        ),
    ]
