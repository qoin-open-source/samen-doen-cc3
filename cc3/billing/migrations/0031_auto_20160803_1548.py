# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0030_auto_20160803_1540'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='invoice_set',
            field=models.ForeignKey(related_name='invoices', verbose_name='Invoice set', to='billing.InvoiceSet'),
        ),
    ]
