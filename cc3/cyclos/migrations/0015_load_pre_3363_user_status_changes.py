# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import pytz
import datetime
from django.utils import timezone


def populate_pre_fix_3363_user_status_changes(apps, schema_editor):
    User = apps.get_model("cyclos","User")
    UserStatusChangeHistory = apps.get_model("cyclos","UserStatusChangeHistory")
    users = User.objects.all()
    timestamp = pytz.timezone(timezone.get_default_timezone_name()).localize(datetime.datetime(2016,12,31,23,59,59))

    for user in users:
        if not user.is_active:
            user_history = UserStatusChangeHistory.objects.filter(user=user)
            if user_history.count() == 0:
                UserStatusChangeHistory.objects.create(
                                    user=user,
                                    change_author=None,
                                    timestamp=timestamp.astimezone(pytz.utc),
                                    activate=False)


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0014_auto_20170214_1635'),
    ]

    operations = [
        migrations.RunPython(populate_pre_fix_3363_user_status_changes),
    ]
