# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaigncategory',
            name='order',
            field=models.PositiveIntegerField(default=0, editable=False, db_index=True),
        ),
    ]
