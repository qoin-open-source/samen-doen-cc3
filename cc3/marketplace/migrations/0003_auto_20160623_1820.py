# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0002_auto_20160616_1053'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adimage',
            name='user_created',
            field=models.ForeignKey(verbose_name='Created by', blank=True, to='cyclos.User', null=True),
        ),
        migrations.AlterField(
            model_name='preadimage',
            name='user_created',
            field=models.ForeignKey(verbose_name='Created by', blank=True, to='cyclos.User', null=True),
        ),
    ]
