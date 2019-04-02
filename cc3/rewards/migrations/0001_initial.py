# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0003_auto_20160609_1610'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusinessCauseSettings',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('transaction_percentage', models.DecimalField(decimal_places=2, max_digits=5, blank=True, help_text='Percentage of each transaction to be rewarded in Samen Doen', null=True, verbose_name='transaction percentage')),
                ('reward_percentage', models.BooleanField(default=False, help_text='Wanneer aangevinkt moet de operator het aankoopbedrag invoeren en wordt de beloning in positoos automatisch berekend als percentage van het aankoopbedrag. Wanneer niet aangevinkt moet de operator zelf het aantal Samen Doen invoeren', verbose_name='reward by percentage')),
                ('user', models.OneToOneField(verbose_name='business', to='cyclos.User')),
            ],
            options={
                'ordering': ('user__email',),
                'verbose_name': 'Business reward settings',
                'verbose_name_plural': 'Business reward settings',
            },
        ),
        migrations.CreateModel(
            name='DefaultGoodCause',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cause', models.ForeignKey(related_name='default_good_cause', verbose_name='default good cause', to='cyclos.User')),
                ('community', models.ForeignKey(verbose_name='community', to='cyclos.CC3Community')),
            ],
        ),
        migrations.CreateModel(
            name='UserCause',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cause', models.ForeignKey(related_name='committed_with', verbose_name='cause', to='cyclos.User')),
                ('consumer', models.OneToOneField(verbose_name='consumer', to='cyclos.User')),
            ],
            options={
                'ordering': ('consumer__email',),
            },
        ),
        migrations.AlterUniqueTogether(
            name='defaultgoodcause',
            unique_together=set([('community', 'cause')]),
        ),
    ]
