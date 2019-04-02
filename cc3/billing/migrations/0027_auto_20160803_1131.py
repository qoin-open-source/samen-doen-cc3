# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0026_auto_20160802_1220'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productpricing',
            name='type',
        ),
        migrations.AddField(
            model_name='product',
            name='cost_centre',
            field=models.CharField(default=b'TODO', max_length=20, verbose_name='Cost centre', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='price_type',
            field=models.CharField(default=b'UNIT', max_length=20, verbose_name='Price type', choices=[(b'UNIT', 'Unit price'), (b'TERM_UNIT', 'Per-terminal charge'), (b'TERM_MINUS_ONE_UNIT', 'Per-terminal charge --  first one free'), (b'SIM_UNIT', 'Per-SIM-card charge')]),
        ),
        migrations.AlterField(
            model_name='assignedproduct',
            name='start_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Start date'),
        ),
        migrations.AlterField(
            model_name='productpricing',
            name='valid_from',
            field=models.DateField(default=datetime.date.today, verbose_name='Valid from'),
        ),
    ]
