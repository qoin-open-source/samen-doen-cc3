# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0011_auto_20170214_0016'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userstatuschangehistory',
            name='change_author',
            field=models.ForeignKey(related_name='change_author', blank=True, to='cyclos.User'),
        ),
    ]
