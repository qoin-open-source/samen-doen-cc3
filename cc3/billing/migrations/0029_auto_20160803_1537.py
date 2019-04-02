# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0028_auto_20160803_1246'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoiceset',
            name='invoices',
        ),
        migrations.AddField(
            model_name='invoice',
            name='invoice_set',
            field=models.ForeignKey(related_name='invoices', verbose_name='Invoice set', blank=True, to='billing.InvoiceSet', null=True),
        ),
    ]
