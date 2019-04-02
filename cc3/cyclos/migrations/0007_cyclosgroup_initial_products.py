# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0040_auto_20160907_1535'),
        ('cyclos', '0006_auto_20160622_1540'),
    ]

    operations = [
        migrations.AddField(
            model_name='cyclosgroup',
            name='initial_products',
            field=models.ManyToManyField(help_text=b'Auto-assigned to new users belonging to this group', related_name='assign_to_groups', to='billing.Product', blank=True),
        ),
    ]
