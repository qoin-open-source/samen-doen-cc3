# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0011_auto_20160712_1144'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxregime',
            name='twinfield_code',
            field=models.CharField(default=b'??', max_length=2, verbose_name='2-letter Twinfield code', validators=[django.core.validators.MinLengthValidator(2)]),
        ),
        migrations.AlterField(
            model_name='product',
            name='billing_frequency',
            field=models.CharField(default=b'ONEOFF', max_length=12, verbose_name='Billing frequency', choices=[(b'ONEOFF', 'One-off'), (b'YEARLY', 'Yearly'), (b'MONTHLY', 'Monthly')]),
        ),
    ]
