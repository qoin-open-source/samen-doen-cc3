# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0007_cyclosgroup_initial_products'),
        ('billing', '0042_auto_20160914_1306'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityProductUserProfileProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'User',
                'proxy': True,
                'verbose_name_plural': 'Users',
            },
            bases=('cyclos.cc3profile',),
        ),
        migrations.AddField(
            model_name='invoiceset',
            name='log_messages',
            field=models.TextField(verbose_name='Log of messages', blank=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(default=b'OTHER', max_length=20, verbose_name='Category', choices=[(b'SUBSCRIPTION', 'Subscriptions'), (b'TERMINALS', 'Cards and terminals'), (b'TRANSACTIONS', 'Transaction charges'), (b'OTHER', 'Other')]),
        ),
    ]
