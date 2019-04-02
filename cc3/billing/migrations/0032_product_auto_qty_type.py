# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0031_auto_20160803_1548'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='auto_qty_type',
            field=models.CharField(blank=True, help_text='Leave blank if set manually by admins', max_length=20, verbose_name='Auto-quantity type', choices=[(b'NUM_TERMINALS', 'Number of terminals assigned'), (b'NUM_TERMINALS-1', 'Number of extra terminals assigned (first is free)')]),
        ),
    ]
