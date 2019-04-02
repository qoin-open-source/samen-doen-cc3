# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0038_auto_20160907_1132'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='transactionparams',
            options={'verbose_name_plural': 'Transaction parameters'},
        ),
        migrations.AddField(
            model_name='assignedproduct',
            name='value',
            field=models.FloatField(help_text='For percentage-based prices only', null=True, verbose_name='Value', blank=True),
        ),
        migrations.AlterField(
            model_name='transactionparams',
            name='product',
            field=models.OneToOneField(related_name='transaction_params', to='billing.Product'),
        ),
    ]
