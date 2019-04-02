# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0006_auto_20160622_1540'),
        ('billing', '0037_auto_20160905_1714'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransactionParams',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('txn_type_id', models.IntegerField(verbose_name='Transaction Type ID')),
                ('invoice_sender', models.BooleanField(verbose_name='Invoice sender?')),
                ('invoice_recipient', models.BooleanField(verbose_name='Invoice recipient?')),
                ('negate_amounts', models.BooleanField(default=False, verbose_name='Negate transaction amounts?')),
            ],
            options={
                'verbose_name': 'Transaction params',
            },
        ),
        migrations.AlterField(
            model_name='product',
            name='auto_assign_type',
            field=models.CharField(blank=True, help_text='Leave blank if assigned manually by admins', max_length=20, verbose_name='Auto-assign type', choices=[(b'TERMINAL_DEPOSIT', 'When terminal assigned to user'), (b'TERMINAL_REFUND', 'When terminal unassigned from user'), (b'TERMINAL_RENTAL', 'To all terminal holders (excl. free ones)'), (b'SIM_CARD', 'To all SIM card holders'), (b'TRANSACTIONS', 'All users making relevant transactions')]),
        ),
        migrations.AlterField(
            model_name='product',
            name='auto_qty_type',
            field=models.CharField(blank=True, help_text='Leave blank if set manually by admins', max_length=20, verbose_name='Auto-quantity type', choices=[(b'NUM_TERMINALS', 'Number of terminals assigned'), (b'NUM_TERMINALS-1', 'Number of extra terminals assigned (first is free)'), (b'NUM_SIM_CARDS', 'Number of SIM cards assigned'), (b'TRANSACTION_VALUE', 'Transaction value')]),
        ),
        migrations.AlterField(
            model_name='product',
            name='price_type',
            field=models.CharField(default=b'UNIT', max_length=20, verbose_name='Price type', choices=[(b'UNIT', 'Unit price'), (b'PERCENTAGE', 'Percentage of value')]),
        ),
        migrations.AddField(
            model_name='transactionparams',
            name='product',
            field=models.OneToOneField(to='billing.Product'),
        ),
        migrations.AddField(
            model_name='transactionparams',
            name='recipient_group',
            field=models.ForeignKey(related_name='uniq2', verbose_name='Receiver group', blank=True, to='cyclos.CyclosGroup', null=True),
        ),
        migrations.AddField(
            model_name='transactionparams',
            name='sender_group',
            field=models.ForeignKey(related_name='uniq1', verbose_name='Sender group', blank=True, to='cyclos.CyclosGroup', null=True),
        ),
    ]
