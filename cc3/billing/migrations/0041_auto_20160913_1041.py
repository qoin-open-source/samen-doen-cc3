# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0040_auto_20160907_1535'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='max_qty',
            field=models.IntegerField(help_text='Maximum for Assigned Product quantity -- leave blank if no limit', null=True, verbose_name='Maximum quantity', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='min_qty',
            field=models.IntegerField(default=0, help_text='Mimimum for Assigned Product quantity', verbose_name='Minimum quantity'),
        ),
        migrations.AlterField(
            model_name='product',
            name='auto_qty_type',
            field=models.CharField(blank=True, help_text='Leave blank if set manually by admins', max_length=20, verbose_name='Auto-quantity/value type', choices=[(b'NUM_TERMINALS', 'Number of terminals assigned'), (b'NUM_TERMINALS-1', 'Number of extra terminals assigned (first is free)'), (b'NUM_SIM_CARDS', 'Number of SIM cards assigned'), (b'TRANSACTION_COUNT', 'Number of transactions'), (b'TRANSACTION_VALUE', 'Value of transactions')]),
        ),
    ]
