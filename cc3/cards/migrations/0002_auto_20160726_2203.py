# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='terminal',
            name='comments',
            field=models.TextField(verbose_name='Comments/Notes', blank=True),
        ),
        migrations.AddField(
            model_name='terminal',
            name='icc_id',
            field=models.CharField(blank=True, max_length=24, verbose_name='ICCID', validators=[django.core.validators.RegexValidator(regex=b'^\\d{18}$', message='ICCID must be 18 digits', code=b'invalid_iccid')]),
        ),
        migrations.AddField(
            model_name='terminal',
            name='removed_date',
            field=models.DateField(null=True, verbose_name='Date removed', blank=True),
        ),
        migrations.AlterField(
            model_name='terminal',
            name='creation_date',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Date created'),
        ),
        migrations.AlterField(
            model_name='terminal',
            name='last_seen_date',
            field=models.DateTimeField(null=True, verbose_name='Date last seen', blank=True),
        ),
    ]
