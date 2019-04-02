# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rewards', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='businesscausesettings',
            name='transaction_percentage',
            field=models.DecimalField(decimal_places=2, max_digits=5, blank=True, help_text='Percentage van elke transactie dat als beloning in Positoos wordt uitbetaald Samen Doen', null=True, verbose_name='transaction percentage'),
        ),
    ]
