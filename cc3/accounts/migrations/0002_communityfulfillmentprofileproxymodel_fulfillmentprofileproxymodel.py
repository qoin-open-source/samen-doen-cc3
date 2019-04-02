# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0016_auto_20170306_1737'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FulfillmentProfileProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'CC3Profile (Fulfillment)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Profile (Fulfillment)',
            },
            bases=('cyclos.cc3profile',),
        ),
        migrations.CreateModel(
            name='CommunityFulfillmentProfileProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'Profile (Fulfillment)',
                'proxy': True,
                'verbose_name_plural': 'Profiles (Fulfillment)',
            },
            bases=('cyclos.cc3profile',),
        ),
    ]
