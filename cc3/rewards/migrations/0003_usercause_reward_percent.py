# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rewards', '0002_auto_20160616_1053'),
    ]

    operations = [
        migrations.AddField(
            model_name='usercause',
            name='reward_percent',
            field=models.IntegerField(null=True, verbose_name='good causes donation percentage', blank=True),
        ),
    ]
