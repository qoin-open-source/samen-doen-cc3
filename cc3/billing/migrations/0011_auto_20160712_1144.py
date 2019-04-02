# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0006_auto_20160622_1540'),
        ('billing', '0010_auto_20160707_1226'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('invoice_date', models.DateField(verbose_name='Invoice date')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('date_exported', models.DateField(null=True, verbose_name='Date exported to TwinField', blank=True)),
                ('user_profile', models.ForeignKey(related_name='invoices', verbose_name='User profile', to='cyclos.CC3Profile')),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payment_for_date', models.DateField(verbose_name='Date payment is for')),
                ('quantity', models.IntegerField(verbose_name='Quantity')),
                ('unit_price_ex_tax', models.DecimalField(verbose_name='Unit price excl. tax (Euro)', max_digits=10, decimal_places=2)),
                ('assigned_product', models.ForeignKey(verbose_name='Assigned product', to='billing.AssignedProduct')),
                ('invoice', models.ForeignKey(related_name='items', verbose_name='Invoice', to='billing.Invoice')),
            ],
        ),
        migrations.RemoveField(
            model_name='invoiceline',
            name='assigned_product',
        ),
        migrations.RemoveField(
            model_name='invoiceline',
            name='invoice_run',
        ),
        migrations.DeleteModel(
            name='InvoiceLine',
        ),
        migrations.DeleteModel(
            name='InvoiceRun',
        ),
    ]
