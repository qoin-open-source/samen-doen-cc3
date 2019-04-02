# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20160609_1608'),
        ('cyclos', '0003_auto_20160609_1610'),
    ]

    operations = [
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('card_security_code', models.CharField(max_length=64, null=True, blank=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('activation_date', models.DateTimeField(null=True, blank=True)),
                ('expiration_date', models.DateField(null=True, blank=True)),
                ('card_security_code_blocked_until', models.DateTimeField(null=True, blank=True)),
                ('status', models.CharField(default=b'A', max_length=1, verbose_name='Status', choices=[(b'A', 'Active'), (b'P', 'Pending'), (b'B', 'Blocked'), (b'D', 'Denied')])),
            ],
            options={
                'ordering': ('-creation_date', '-number', '-activation_date', 'owner'),
            },
        ),
        migrations.CreateModel(
            name='CardNumber',
            fields=[
                ('uid_number', models.CharField(unique=True, max_length=50, verbose_name='Card UID')),
                ('number', models.BigIntegerField(unique=True, serialize=False, verbose_name='Card number', primary_key=True, validators=[django.core.validators.MaxValueValidator(99999), django.core.validators.MinValueValidator(0)])),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ('-number',),
            },
        ),
        migrations.CreateModel(
            name='CardRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('registration_choice', models.CharField(max_length=5, verbose_name='Registration Choice', choices=[(b'Old', 'I have an old card to replace'), (b'Send', 'Order another card')])),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(related_name='card_registration_set', verbose_name='Owner', to='cyclos.User')),
            ],
            options={
                'ordering': ('-creation_date',),
            },
        ),
        migrations.CreateModel(
            name='CardTransaction',
            fields=[
                ('transaction_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='core.Transaction')),
                ('description', models.CharField(max_length=255, verbose_name='description', blank=True)),
                ('card', models.ForeignKey(related_name='card_transaction_set', verbose_name='card', to='cards.Card')),
            ],
            bases=('core.transaction',),
        ),
        migrations.CreateModel(
            name='CardType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Card name')),
                ('default', models.BooleanField(default=True, help_text='The default type, used for newly registered Cards')),
                ('card_format_number', models.CharField(max_length=56, null=True, blank=True)),
                ('default_expiration_number', models.IntegerField(null=True, blank=True)),
                ('default_expiration_field', models.IntegerField(null=True, blank=True)),
                ('card_security_code', models.CharField(max_length=1, null=True, blank=True)),
                ('show_card_security_code', models.BooleanField(default=False)),
                ('ignore_day_in_expiration_date', models.BooleanField(default=False)),
                ('min_card_security_code_length', models.IntegerField(null=True, blank=True)),
                ('max_card_security_code_length', models.IntegerField(null=True, blank=True)),
                ('security_code_block_times_number', models.IntegerField(null=True, blank=True)),
                ('security_code_block_times_field', models.IntegerField(null=True, blank=True)),
                ('max_security_code_tries', models.IntegerField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Fulfillment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(max_length=25, verbose_name='Status', choices=[(b'New', 'New'), (b'Manually Processed', 'Manually Processed'), (b'Account Closed', 'Cancelled (Account closed)')])),
                ('card_registration', models.ForeignKey(to='cards.CardRegistration')),
                ('profile', models.ForeignKey(to='cyclos.CC3Profile')),
            ],
            options={
                'ordering': ('-status', '-last_modified'),
            },
        ),
        migrations.CreateModel(
            name='Operator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('pin', models.CharField(max_length=4)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('last_login_date', models.DateTimeField(null=True, blank=True)),
                ('business', models.ForeignKey(related_name='operator_set', verbose_name='Business', to='cyclos.User')),
            ],
        ),
        migrations.CreateModel(
            name='Terminal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='IMEI')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('last_seen_date', models.DateTimeField(null=True, blank=True)),
                ('business', models.ForeignKey(related_name='terminal_set', verbose_name='Business', blank=True, to='cyclos.User', null=True)),
            ],
        ),
        migrations.AddField(
            model_name='cardtransaction',
            name='operator',
            field=models.ForeignKey(related_name='card_transaction_set', verbose_name='operator', to='cards.Operator'),
        ),
        migrations.AddField(
            model_name='cardtransaction',
            name='terminal',
            field=models.ForeignKey(related_name='card_transaction_set', verbose_name='terminal', to='cards.Terminal'),
        ),
        migrations.AddField(
            model_name='card',
            name='card_type',
            field=models.ForeignKey(verbose_name='Card type', to='cards.CardType'),
        ),
        migrations.AddField(
            model_name='card',
            name='number',
            field=models.OneToOneField(null=True, verbose_name='Card number', to='cards.CardNumber'),
        ),
        migrations.AddField(
            model_name='card',
            name='owner',
            field=models.ForeignKey(related_name='card_set', verbose_name='Owner', to='cyclos.User'),
        ),
        migrations.AlterUniqueTogether(
            name='operator',
            unique_together=set([('name', 'business')]),
        ),
    ]
