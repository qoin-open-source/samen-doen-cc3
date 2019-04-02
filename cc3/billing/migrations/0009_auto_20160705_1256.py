# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0008_auto_20160704_1231'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='description',
        ),
        migrations.AddField(
            model_name='product',
            name='article_code',
            field=models.CharField(default='XXXX', max_length=20, verbose_name='Article code'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='subarticle_code',
            field=models.CharField(max_length=20, verbose_name='Sub-article code', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='subname',
            field=models.CharField(max_length=100, verbose_name='Sub-name', blank=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='invoiced_by',
            field=models.ForeignKey(related_name='products', verbose_name='Invoiced company', blank=True, to='billing.Supplier', null=True),
        ),
    ]
