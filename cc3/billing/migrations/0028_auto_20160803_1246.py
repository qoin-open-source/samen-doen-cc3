# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0027_auto_20160803_1131'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='terminaldeposit',
            name='charged_in_invoice',
        ),
        migrations.RemoveField(
            model_name='terminaldeposit',
            name='refunded_in_invoice',
        ),
        migrations.AddField(
            model_name='product',
            name='auto_assign_type',
            field=models.CharField(blank=True, help_text='Leave blank if assigned manually by admins', max_length=20, verbose_name='Auto-assign type', choices=[(b'TERMINAL_DEPOSIT', 'Deposit for terminal'), (b'TERMINAL_REFUND', 'Refund of terminal deposit')]),
        ),
        migrations.AddField(
            model_name='terminaldeposit',
            name='date_deposit_charged',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='terminaldeposit',
            name='date_deposit_refunded',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
