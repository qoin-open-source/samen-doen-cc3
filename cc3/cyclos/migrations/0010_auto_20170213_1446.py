# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0009_auto_20161026_1348'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserStatusChangeHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=datetime.datetime(2016, 12, 31, 23, 59, 59, tzinfo=utc))),
                ('activate', models.BooleanField(default=True)),
                ('change_author', models.ForeignKey(related_name='change_author', to='cyclos.User')),
                ('target_user', models.ForeignKey(related_name='target_user', to='cyclos.User')),
            ],
        ),
        migrations.AlterField(
            model_name='communitypluginmodel',
            name='cmsplugin_ptr',
            field=models.OneToOneField(parent_link=True, related_name='cyclos_communitypluginmodel', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
    ]
