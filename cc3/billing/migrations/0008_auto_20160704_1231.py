# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_auto_20160704_1123'),
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('company_name', models.CharField(max_length=100, verbose_name='Name')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='invoiced_by',
            field=models.ForeignKey(related_name='products', verbose_name='Invoiced by', blank=True, to='billing.Supplier', null=True),
        ),
    ]
