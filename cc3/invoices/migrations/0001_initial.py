# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('code', models.CharField(max_length=3, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=32)),
                ('symbol', models.CharField(max_length=12)),
            ],
            options={
                'ordering': ('code',),
                'verbose_name_plural': 'currencies',
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(unique=True, blank=True)),
                ('inv_date', models.DateField()),
                ('due_date', models.DateField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('automatic_invoice', models.BooleanField(default=False, help_text='If this invoice was automatically generated')),
                ('admin_comment', models.TextField(help_text='Comment field for admin users, not shown to users', blank=True)),
                ('invoice_type', models.CharField(default=b'debit', max_length=20, choices=[(b'debit', b'Debit'), (b'credit', b'Credit')])),
                ('currency', models.ForeignKey(to='invoices.Currency')),
            ],
            options={
                'ordering': ('number',),
            },
        ),
        migrations.CreateModel(
            name='InvoiceLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=255)),
                ('quantity', models.IntegerField()),
                ('amount', models.DecimalField(max_digits=12, decimal_places=4)),
                ('tax_rate', models.DecimalField(default=21, max_digits=12, decimal_places=4)),
                ('net_total', models.DecimalField(max_digits=12, decimal_places=4, blank=True)),
                ('grand_total', models.DecimalField(max_digits=12, decimal_places=4, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('invoice', models.ForeignKey(related_name='lines', to='invoices.Invoice')),
            ],
            options={
                'ordering': ('invoice__number', 'description'),
            },
        ),
        migrations.CreateModel(
            name='PaymentStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=255)),
                ('is_active', models.BooleanField()),
                ('is_paid', models.BooleanField()),
            ],
            options={
                'ordering': ('description',),
                'verbose_name_plural': 'payment statuses',
            },
        ),
        migrations.AddField(
            model_name='invoice',
            name='payment_status',
            field=models.ForeignKey(to='invoices.PaymentStatus'),
        ),
    ]
