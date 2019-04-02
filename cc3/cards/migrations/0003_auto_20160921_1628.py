# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0002_auto_20160726_2203'),
    ]

    operations = [
        migrations.AlterField(
            model_name='terminal',
            name='icc_id',
            field=models.CharField(blank=True, max_length=24, verbose_name='ICCID', validators=[django.core.validators.RegexValidator(regex=b'^\\d{19,20}$', message='ICCID must be 19 or 20 digits', code=b'invalid_iccid')]),
        ),
    ]
