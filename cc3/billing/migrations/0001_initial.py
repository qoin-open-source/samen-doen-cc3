# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0006_auto_20160622_1540'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignedProduct',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateField(verbose_name='Start date')),
                ('end_date', models.DateField(null=True, verbose_name='End date', blank=True)),
                ('quantity', models.IntegerField(verbose_name='Quantity')),
                ('discount_applied', models.DecimalField(default=0, verbose_name='Discount applied (%)', max_digits=5, decimal_places=2)),
                ('date_invoiced', models.DateField(null=True, verbose_name='Date invoiced', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.CharField(max_length=1000, verbose_name='Description')),
                ('max_discount_percent', models.DecimalField(default=0, verbose_name='Maximum discount (%)', max_digits=5, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='ProductPricing',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateField(verbose_name='Start date')),
                ('end_date', models.DateField(null=True, verbose_name='End date', blank=True)),
                ('product', models.ForeignKey(related_name='prices', verbose_name='Product', to='billing.Product')),
            ],
        ),
        migrations.CreateModel(
            name='TaxRegime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('percentage', models.DecimalField(null=True, max_digits=5, decimal_places=2, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='tax_regime',
            field=models.ForeignKey(verbose_name='Tax regime', to='billing.TaxRegime'),
        ),
        migrations.AddField(
            model_name='product',
            name='user_groups',
            field=models.ManyToManyField(related_name='products', verbose_name='User groups', to='cyclos.CyclosGroup'),
        ),
        migrations.AddField(
            model_name='assignedproduct',
            name='pricing_applied',
            field=models.ForeignKey(verbose_name='Pricing applied', to='billing.ProductPricing'),
        ),
        migrations.AddField(
            model_name='assignedproduct',
            name='product',
            field=models.ForeignKey(related_name='assignments', verbose_name='Assigned to user', to='billing.Product'),
        ),
        migrations.AddField(
            model_name='assignedproduct',
            name='user_profile',
            field=models.ForeignKey(related_name='assigned_products', verbose_name='Assigned to user', to='cyclos.CC3Profile'),
        ),
    ]
