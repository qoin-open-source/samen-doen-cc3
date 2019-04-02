# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0004_businessuserproxymodel_cardmachineuserproxymodel_carduserproxymodel_charityuserproxymodel_institutio'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cc3profile',
            name='registration_number',
        ),
        migrations.AlterField(
            model_name='cycloschannel',
            name='order',
            field=models.PositiveIntegerField(default=0, editable=False, db_index=True),
        ),
    ]
