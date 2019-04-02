# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0018_auto_20160718_1558'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='invoicing_company',
            field=models.ForeignKey(related_name='invoices', verbose_name='Invoicing company', to='billing.InvoicingCompany'),
        ),
        migrations.AlterField(
            model_name='product',
            name='invoiced_by',
            field=models.ForeignKey(related_name='products', verbose_name='Invoicing company', to='billing.InvoicingCompany'),
        ),
    ]
