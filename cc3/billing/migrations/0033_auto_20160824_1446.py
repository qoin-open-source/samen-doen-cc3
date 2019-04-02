# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0032_product_auto_qty_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='BillingSettings',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('TWINFIELD_GL_ACCOUNT', models.CharField(default=b'8000', max_length=20, verbose_name='Twinfield GL account')),
                ('TWINFIELD_CREDIT_MANAGER', models.CharField(default=b'QOIN2', max_length=20, verbose_name='Twinfield credit manager')),
                ('TWINFIELD_USER_CODE_TEMPLATE', models.CharField(default=b'SD{0:06d}', max_length=20, verbose_name='Twinfield user code template')),
                ('TWINFIELD_INVOICE_TYPE', models.CharField(default=b'01', max_length=20, verbose_name='Twinfield invoice type')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='product',
            name='auto_assign_type',
            field=models.CharField(blank=True, help_text='Leave blank if assigned manually by admins', max_length=20, verbose_name='Auto-assign type', choices=[(b'TERMINAL_DEPOSIT', 'When terminal assigned to user'), (b'TERMINAL_REFUND', 'When terminal unassigned from user'), (b'TERMINAL_RENTAL', 'To all terminal holders (excl. free ones)')]),
        ),
        migrations.AlterField(
            model_name='product',
            name='price_type',
            field=models.CharField(default=b'UNIT', max_length=20, verbose_name='Price type', choices=[(b'UNIT', 'Unit price')]),
        ),
    ]
