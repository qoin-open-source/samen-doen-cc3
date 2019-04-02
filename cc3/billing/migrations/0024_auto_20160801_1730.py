# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0002_auto_20160726_2203'),
        ('cyclos', '0006_auto_20160622_1540'),
        ('billing', '0023_auto_20160726_1719'),
    ]

    operations = [
        migrations.CreateModel(
            name='TerminalDeposit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('deposit_due', models.BooleanField(default=True)),
                ('refund_due', models.BooleanField(default=False)),
                ('business', models.ForeignKey(verbose_name='Business', to='cyclos.User')),
                ('charged_in_invoice', models.ForeignKey(related_name='deposits_charged', verbose_name='Invoice where deposit was charged', blank=True, to='billing.Invoice', null=True)),
                ('refunded_in_invoice', models.ForeignKey(related_name='deposits_refunded', verbose_name='Invoice where deposit was refunded', blank=True, to='billing.Invoice', null=True)),
                ('terminal', models.ForeignKey(verbose_name='Terminal', to='cards.Terminal')),
            ],
        ),
        migrations.AlterField(
            model_name='invoiceset',
            name='generated_at',
            field=models.DateTimeField(null=True, verbose_name='Generated at', blank=True),
        ),
        migrations.AlterField(
            model_name='invoiceset',
            name='sent_at',
            field=models.DateTimeField(null=True, verbose_name='Sent at', blank=True),
        ),
        migrations.AlterField(
            model_name='invoiceset',
            name='sent_to',
            field=models.TextField(verbose_name='Sent to', blank=True),
        ),
        migrations.AlterField(
            model_name='productpricing',
            name='type',
            field=models.CharField(default=b'UNIT', max_length=20, verbose_name='Price type', choices=[(b'UNIT', 'Unit price'), (b'TERM_UNIT', 'Per-terminal charge'), (b'TERM_MINUS_ONE_UNIT', 'Per-terminal charge --  first one free'), (b'TERM_DEPOSIT', 'Terminal deposit'), (b'SIM_UNIT', 'Per-SIM-card charge')]),
        ),
    ]
