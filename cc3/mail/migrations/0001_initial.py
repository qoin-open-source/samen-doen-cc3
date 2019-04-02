# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import cc3.core.utils


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('attachment', models.FileField(upload_to=cc3.core.utils.UploadTo(b'attachments'))),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='MailMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(unique=True, max_length=100, choices=[(b'newreg', b'New registration email'), (b'profilecompleted', b'Profile completed email'), (b'newtransaction', b'Transaction completed email'), (b'adonhold', b'New or updated Ad needs approval'), (b'usercard', b'Send user card'), (b'enquiryenquirer', b'Ad enquiry email for enquirer'), (b'enquiryadvertiser', b'Ad enquiry email for advertiser'), (b'enquiryadmins', b'Ad enquiry email for admins'), (b'negbalanceuser', b'Negative balance warning email'), (b'negbalanceadmins', b'Negative balance email for admins'), (b'negbalancecollectuser', b'Negative balance collection email'), (b'negbalancecollectadmins', b'Negative balance collection email for admins'), (b'largebalanceuser', b'Large balance warning email'), (b'largebalanceadmins', b'Large balance email for admins'), (b'matchingcats', b'Daily Matching Wants/Offers email'), (b'updatedcats', b'Profile Updated Wants/Offers email'), (b'exchangetomoney', b'Exchange to Money performed'), (b'bulkpurchase', b'Bulk prizedraw tickets purchased'), (b'prizedrawnewreg', b'Prizedraw new registration email'), (b'monthlyinvoice', b'Notification of monthly invoice'), (b'campaignsignup', b'Campaigns: Confirmation on signing up'), (b'campaignsignupowner', b'Campaigns: Notify owner of new signup'), (b'campaignupdated', b'Campaigns: Notify participants a campaign has been edited'), (b'campaigncancelled', b'Campaigns: Notify participants a campaign has been cancelled'), (b'campaignunsubscribed', b'Campaigns: Notify participant they have been removed'), (b'campaigncreated', b'Campaigns: Notify members of new campaign (optional)')])),
                ('subject', models.CharField(max_length=150)),
                ('body', models.TextField()),
                ('lang', models.CharField(default=b'', help_text=b'Language code, if applicable', max_length=10, blank=True)),
                ('attachments', models.ManyToManyField(to='mail.Attachment', blank=True)),
            ],
            options={
                'verbose_name': 'E-mail template',
                'verbose_name_plural': 'E-mail template',
            },
        ),
    ]
