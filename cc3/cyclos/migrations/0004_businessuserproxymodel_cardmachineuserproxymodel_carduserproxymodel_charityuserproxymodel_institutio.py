# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.auth.models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0003_auto_20160609_1610'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusinessUserProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'User (Business)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Users (Businesses)',
            },
            bases=('cyclos.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='CardMachineUserProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'User (Card Machine)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Users (Card Machine)',
            },
            bases=('cyclos.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='CardUserProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'User (Card)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Users (Card)',
            },
            bases=('cyclos.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='CharityUserProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'User (Charity)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Users (Charity)',
            },
            bases=('cyclos.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='InstitutionUserProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'User (Institution)',
                'managed': False,
                'proxy': True,
                'verbose_name_plural': 'Users (Institutions)',
            },
            bases=('cyclos.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
