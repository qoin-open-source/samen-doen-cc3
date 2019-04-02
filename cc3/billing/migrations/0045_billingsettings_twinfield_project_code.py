# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0044_auto_20160920_1637'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingsettings',
            name='TWINFIELD_PROJECT_CODE',
            field=models.CharField(default=b'P0001', max_length=20, verbose_name='Twinfield Project Code'),
        ),
    ]
