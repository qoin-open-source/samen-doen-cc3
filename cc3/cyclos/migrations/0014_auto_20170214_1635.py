# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0013_auto_20170214_1303'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userstatuschangehistory',
            name='change_author',
            field=models.ForeignKey(related_name='change_author', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='userstatuschangehistory',
            name='user',
            field=models.ForeignKey(related_name='target_user', to=settings.AUTH_USER_MODEL),
        ),
    ]
