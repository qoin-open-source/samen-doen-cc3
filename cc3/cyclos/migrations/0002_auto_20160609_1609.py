# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0002_auto_20160609_1609'),
        ('cyclos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cyclosgroup',
            name='invoice_currency',
            field=models.ForeignKey(blank=True, to='invoices.Currency', help_text='The currency to be used for automatically created invoices. Mandatory if "create monthly invoice" is enabled.', null=True),
        ),
        migrations.AlterField(
            model_name='cyclosgroupset',
            name='groups',
            field=models.ManyToManyField(related_name='groupsets', null=True, to='cyclos.CyclosGroup', blank=True),
        ),
    ]
