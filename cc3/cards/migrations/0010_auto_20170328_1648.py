# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0009_auto_20170328_1645'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BigNumTest',
        ),
        migrations.AlterField(
            model_name='cardnumber',
            name='number',
            field=models.BigIntegerField(unique=True, serialize=False, verbose_name='Card number', primary_key=True, validators=[django.core.validators.MaxValueValidator(9999999999999999), django.core.validators.MinValueValidator(0)]),
        ),
    ]
