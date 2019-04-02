# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0010_auto_20170213_1446'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userstatuschangehistory',
            old_name='target_user',
            new_name='user',
        ),
    ]
