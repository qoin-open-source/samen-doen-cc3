# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0041_auto_20160913_1041'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceset',
            name='invoices_created_at',
            field=models.DateTimeField(null=True, verbose_name='Invoices created at', blank=True),
        ),
        migrations.AlterField(
            model_name='invoiceset',
            name='generated_at',
            field=models.DateTimeField(null=True, verbose_name='Files generated at', blank=True),
        ),
        migrations.AlterField(
            model_name='invoiceset',
            name='sent_at',
            field=models.DateTimeField(null=True, verbose_name='Files sent at', blank=True),
        ),
        migrations.AlterField(
            model_name='invoiceset',
            name='sent_to',
            field=models.TextField(verbose_name='Files sent to', blank=True),
        ),
    ]
