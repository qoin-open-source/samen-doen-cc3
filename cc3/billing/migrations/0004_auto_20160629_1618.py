# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_auto_20160629_1612'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignedproduct',
            name='next_invoice_due',
            field=models.DateField(null=True, verbose_name='Next invoice due date', blank=True),
        ),
        migrations.AlterField(
            model_name='assignedproduct',
            name='date_invoiced',
            field=models.DateField(null=True, verbose_name='Date last invoiced', blank=True),
        ),
    ]
