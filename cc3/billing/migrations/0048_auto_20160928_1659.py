# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0047_auto_20160928_1050'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoiceset',
            name='extras_generated_at',
        ),
        migrations.RemoveField(
            model_name='invoiceset',
            name='log_messages',
        ),
    ]
