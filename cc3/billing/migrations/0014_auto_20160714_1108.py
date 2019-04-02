# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0013_auto_20160713_1706'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='invoicing_company',
            field=models.ForeignKey(related_name='invoices', verbose_name='Invoicing company', blank=True, to='billing.InvoicingCompany', null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='invoiced_by',
            field=models.ForeignKey(related_name='products', verbose_name='Invoicing company', blank=True, to='billing.InvoicingCompany', null=True),
        ),
    ]
