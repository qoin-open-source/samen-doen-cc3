# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0046_auto_20160927_1233'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceset',
            name='period_end',
            field=models.DateField(help_text='Blank for ad-hoc invoices', null=True, verbose_name='Period end date', blank=True),
        ),
        migrations.AddField(
            model_name='invoiceset',
            name='period_start',
            field=models.DateField(help_text='Blank for ad-hoc invoices', null=True, verbose_name='Period start date', blank=True),
        ),
    ]
