# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_auto_20160629_1618'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductPayment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payment_date', models.DateField(verbose_name='Payment date')),
                ('invoice_date', models.DateField(null=True, verbose_name='Date sent for invoicing', blank=True)),
                ('base_price_euros', models.DecimalField(verbose_name='Base price (Euro)', max_digits=10, decimal_places=2)),
                ('discount_percent', models.DecimalField(verbose_name='Discount (%)', max_digits=5, decimal_places=2)),
                ('tax_percent', models.DecimalField(verbose_name='Tax (%)', max_digits=5, decimal_places=2)),
                ('payment_amount_euros', models.DecimalField(verbose_name='Payment amount (Euro)', max_digits=10, decimal_places=2)),
            ],
        ),
        migrations.RenameField(
            model_name='taxregime',
            old_name='percentage',
            new_name='percent',
        ),
        migrations.RemoveField(
            model_name='assignedproduct',
            name='date_invoiced',
        ),
        migrations.RemoveField(
            model_name='assignedproduct',
            name='discount_applied',
        ),
        migrations.RemoveField(
            model_name='assignedproduct',
            name='next_invoice_due',
        ),
        migrations.RemoveField(
            model_name='assignedproduct',
            name='pricing_applied',
        ),
        migrations.AddField(
            model_name='assignedproduct',
            name='discount',
            field=models.DecimalField(default=0, verbose_name='Discount (%)', max_digits=5, decimal_places=2),
        ),
        migrations.AddField(
            model_name='productpayment',
            name='assigned_product',
            field=models.ForeignKey(related_name='payments', verbose_name='Assigned product', to='billing.AssignedProduct'),
        ),
        migrations.AddField(
            model_name='productpayment',
            name='pricing_used',
            field=models.ForeignKey(verbose_name='Pricing used for this payment', to='billing.ProductPricing'),
        ),
    ]
