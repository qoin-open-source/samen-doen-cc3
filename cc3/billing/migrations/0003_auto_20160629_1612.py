# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_auto_20160629_1541'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productpricing',
            options={'ordering': ('-start_date',)},
        ),
        migrations.RemoveField(
            model_name='productpricing',
            name='billing_frequency',
        ),
        migrations.AddField(
            model_name='product',
            name='billing_frequency',
            field=models.CharField(default=b'ONEOFF', max_length=12, verbose_name='Billng frequency', choices=[(b'ONEOFF', 'One-off'), (b'YEARLY', 'Yearly'), (b'MONTHLY', 'Monthly')]),
        ),
    ]
