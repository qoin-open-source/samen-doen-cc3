# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0015_auto_20160421_0000'),
        ('cyclos', '0005_auto_20160616_1053'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('body', models.TextField(blank=True)),
                ('community', models.ForeignKey(blank=True, to='cyclos.CC3Community', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CommunityPluginModel',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('body', models.TextField(blank=True)),
            ],
            bases=('cms.cmsplugin',),
        ),
        migrations.AddField(
            model_name='communitymessage',
            name='plugin',
            field=models.ForeignKey(to='cyclos.CommunityPluginModel'),
        ),
    ]
