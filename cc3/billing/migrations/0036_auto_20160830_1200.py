# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0035_auto_20160829_1649'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='article_code',
            field=models.CharField(max_length=20, verbose_name='Article code'),
        ),
        migrations.AlterField(
            model_name='product',
            name='auto_assign_type',
            field=models.CharField(blank=True, help_text='Leave blank if assigned manually by admins', max_length=20, verbose_name='Auto-assign type', choices=[(b'TERMINAL_DEPOSIT', 'When terminal assigned to user'), (b'TERMINAL_REFUND', 'When terminal unassigned from user'), (b'TERMINAL_RENTAL', 'To all terminal holders (excl. free ones)'), (b'SIM_CARD', 'When SIM card assigned to user')]),
        ),
        migrations.AlterField(
            model_name='product',
            name='auto_qty_type',
            field=models.CharField(blank=True, help_text='Leave blank if set manually by admins', max_length=20, verbose_name='Auto-quantity type', choices=[(b'NUM_TERMINALS', 'Number of terminals assigned'), (b'NUM_TERMINALS-1', 'Number of extra terminals assigned (first is free)'), (b'NUM_SIM_CARDS', 'Number of SIM cards assigned')]),
        ),
    ]
