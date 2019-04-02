# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0012_auto_20160713_1439'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Supplier',
            new_name='InvoicingCompany',
        ),
    ]
