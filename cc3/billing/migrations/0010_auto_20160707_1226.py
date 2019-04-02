# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0009_auto_20160705_1256'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoiceLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payment_for_date', models.DateField(verbose_name='Date payment is for')),
                ('quantity', models.IntegerField(verbose_name='Quantity')),
                ('unit_price_ex_tax', models.DecimalField(verbose_name='Unit price excl. tax (Euro)', max_digits=10, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceRun',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateField(verbose_name='Invoice period start date')),
                ('end_date', models.DateField(verbose_name='Invoice period end date')),
                ('invoice_date', models.DateField(verbose_name='Invoice date')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('status', models.CharField(default=b'NEW', max_length=20, verbose_name='Status', choices=[(b'NEW', 'New'), (b'EXPORTING', 'Export in progress'), (b'EXPORTED', 'Exported')])),
            ],
        ),
        migrations.RemoveField(
            model_name='productpayment',
            name='assigned_product',
        ),
        migrations.RemoveField(
            model_name='productpayment',
            name='pricing_used',
        ),
        migrations.AddField(
            model_name='assignedproduct',
            name='next_invoice_date',
            field=models.DateField(null=True, verbose_name='Date of next payment', blank=True),
        ),
        migrations.DeleteModel(
            name='ProductPayment',
        ),
        migrations.AddField(
            model_name='invoiceline',
            name='assigned_product',
            field=models.ForeignKey(verbose_name='Assigned product', to='billing.AssignedProduct'),
        ),
        migrations.AddField(
            model_name='invoiceline',
            name='invoice_run',
            field=models.ForeignKey(related_name='items', verbose_name='Invoice run', to='billing.InvoiceRun'),
        ),
    ]
