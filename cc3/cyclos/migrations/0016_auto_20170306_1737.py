# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0015_load_pre_3363_user_status_changes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userstatuschangehistory',
            name='timestamp',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 31, 22, 59, 59, tzinfo=utc)),
        ),
    ]
