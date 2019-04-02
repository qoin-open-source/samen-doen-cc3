# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0016_auto_20170306_1737'),
    ]

    operations = [
        migrations.AddField(
            model_name='cc3profile',
            name='original_date_joined',
            field=models.DateTimeField(null=True, verbose_name='Original Date Joined', blank=True),
        ),
        migrations.AlterField(
            model_name='cc3profile',
            name='community',
            field=models.ForeignKey(verbose_name='Community', blank=True, to='cyclos.CC3Community', null=True),
        ),
        migrations.AlterField(
            model_name='cc3profile',
            name='cyclos_group',
            field=models.ForeignKey(verbose_name='Cyclos Group', blank=True, to='cyclos.CyclosGroup', null=True),
        ),
    ]
