# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0006_auto_20160629_1908'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productpricing',
            options={'ordering': ('-valid_from',)},
        ),
        migrations.RemoveField(
            model_name='productpricing',
            name='end_date',
        ),
        migrations.RemoveField(
            model_name='productpricing',
            name='start_date',
        ),
        migrations.AddField(
            model_name='product',
            name='category',
            field=models.CharField(default=b'OTHER', max_length=20, verbose_name='Category', choices=[(b'SUBSCRIPTION', 'Subscriptions'), (b'TERMINALS', 'Cards and terminals'), (b'OTHER', 'Other')]),
        ),
        migrations.AddField(
            model_name='productpricing',
            name='valid_from',
            field=models.DateField(default=datetime.date(2016, 7, 4), verbose_name='Valid from'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productpricing',
            name='valid_to',
            field=models.DateField(null=True, verbose_name='Valid to', blank=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='max_discount_percent',
            field=models.DecimalField(default=0, verbose_name='Maximum discount (%)', max_digits=5, decimal_places=2, validators=[django.core.validators.MaxValueValidator(100.0)]),
        ),
    ]
