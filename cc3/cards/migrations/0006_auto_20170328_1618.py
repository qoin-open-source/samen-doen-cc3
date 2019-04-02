# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0005_auto_20170302_0311'),
    ]

    operations = [
        migrations.CreateModel(
            name='BigNumTest',
            fields=[
                ('number', models.BigIntegerField(unique=True, serialize=False, verbose_name='Big number test', primary_key=True)),
            ],
        ),
        migrations.AlterField(
            model_name='cardnumber',
            name='number',
            field=models.BigIntegerField(unique=True, serialize=False, verbose_name='Card number', primary_key=True, validators=[django.core.validators.MaxValueValidator(4294967297), django.core.validators.MinValueValidator(0)]),
        ),
    ]
