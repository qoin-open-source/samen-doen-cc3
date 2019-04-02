# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='productpricing',
            name='billing_frequency',
            field=models.CharField(default=b'ONEOFF', max_length=12, verbose_name='Billng frequency', choices=[(b'ONEOFF', 'One-off'), (b'YEARLY', 'Yearly'), (b'MONTHLY', 'Monthly')]),
        ),
        migrations.AddField(
            model_name='productpricing',
            name='unit_price_euros',
            field=models.DecimalField(default=0, verbose_name='Unit price (Euro)', max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='assignedproduct',
            name='product',
            field=models.ForeignKey(related_name='assignments', verbose_name='Product', to='billing.Product'),
        ),
    ]
