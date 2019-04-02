# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0012_auto_20170411_2336'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fulfillment',
            name='card_registration',
            field=models.ForeignKey(blank=True, to='cards.CardRegistration', null=True),
        ),
    ]
