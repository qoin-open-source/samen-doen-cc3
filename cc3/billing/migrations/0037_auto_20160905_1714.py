# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0036_auto_20160830_1200'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='assignedproduct',
            options={'ordering': ('-next_invoice_date',)},
        ),
        migrations.AlterField(
            model_name='assignedproduct',
            name='discount_percent',
            field=models.IntegerField(default=0, verbose_name='Discount (%)'),
        ),
        migrations.AlterField(
            model_name='assignedproduct',
            name='quantity',
            field=models.IntegerField(help_text='Auto-calculated for rentals and subsciptions', verbose_name='Quantity'),
        ),
        migrations.AlterField(
            model_name='product',
            name='auto_assign_type',
            field=models.CharField(blank=True, help_text='Leave blank if assigned manually by admins', max_length=20, verbose_name='Auto-assign type', choices=[(b'TERMINAL_DEPOSIT', 'When terminal assigned to user'), (b'TERMINAL_REFUND', 'When terminal unassigned from user'), (b'TERMINAL_RENTAL', 'To all terminal holders (excl. free ones)'), (b'SIM_CARD', 'To all SIM card holders')]),
        ),
        migrations.AlterField(
            model_name='product',
            name='max_discount_percent',
            field=models.IntegerField(default=0, verbose_name='Maximum discount (%)', validators=[django.core.validators.MaxValueValidator(100)]),
        ),
    ]
