# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0015_auto_20160718_1118'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignedproduct',
            name='billing_frequency',
            field=models.CharField(blank=True, max_length=12, null=True, verbose_name='Billing frequency', choices=[(b'ONEOFF', 'One-off'), (b'YEARLY', 'Yearly'), (b'MONTHLY', 'Monthly')]),
        ),
    ]
