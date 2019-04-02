# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0007_auto_20170328_1621'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cardnumber',
            name='number',
            field=models.IntegerField(unique=True, serialize=False, verbose_name='Card number', primary_key=True),
        ),
    ]
