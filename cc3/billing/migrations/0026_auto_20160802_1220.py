# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0025_auto_20160801_1734'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='terminaldeposit',
            unique_together=set([('business', 'terminal')]),
        ),
    ]
