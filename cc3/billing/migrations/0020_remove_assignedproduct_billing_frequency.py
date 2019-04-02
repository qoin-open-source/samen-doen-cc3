# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0019_auto_20160718_1628'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assignedproduct',
            name='billing_frequency',
        ),
    ]
