# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0004_auto_20170302_0306'),
    ]

    operations = [
        migrations.RenameField(
            model_name='fulfillment',
            old_name='number',
            new_name='card',
        ),
    ]
