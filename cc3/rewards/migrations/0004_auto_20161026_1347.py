# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rewards', '0003_usercause_reward_percent'),
    ]

    operations = [
        migrations.RenameField(
            model_name='usercause',
            old_name='reward_percent',
            new_name='donation_percent',
        ),
    ]
