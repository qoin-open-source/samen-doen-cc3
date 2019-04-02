# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0021_auto_20160719_1703'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoiceitem',
            name='discount_amount',
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='discount_amount_ex_tax',
            field=models.DecimalField(default=0, help_text='This is a negative amount (or zero)', verbose_name='Discount excl. tax (Euro)', max_digits=10, decimal_places=2),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='discount_amount_incl_tax',
            field=models.DecimalField(default=0, help_text='This is a negative amount (or zero)', verbose_name='Discount incl. tax (Euro)', max_digits=10, decimal_places=2),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='tax_name',
            field=models.CharField(default='-', max_length=100, verbose_name='Name'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='tax_percent',
            field=models.DecimalField(null=True, verbose_name='% rate', max_digits=5, decimal_places=2, blank=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='unit_price_incl_tax',
            field=models.DecimalField(default=99.99, verbose_name='Unit price incl. tax (Euro)', max_digits=10, decimal_places=2),
            preserve_default=False,
        ),
    ]
