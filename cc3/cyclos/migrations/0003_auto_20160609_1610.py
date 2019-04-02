# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0002_auto_20160609_1609'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cyclosgroupset',
            name='groups',
            field=models.ManyToManyField(related_name='groupsets', to='cyclos.CyclosGroup', blank=True),
        ),
    ]
