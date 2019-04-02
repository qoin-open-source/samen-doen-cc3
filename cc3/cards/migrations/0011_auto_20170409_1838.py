# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0010_auto_20170328_1648'),
    ]

    operations = [
        migrations.AlterField(
            model_name='card',
            name='owner',
            field=models.ForeignKey(related_name='card_set', verbose_name='Owner', blank=True, to='cyclos.User', null=True),
        ),
    ]
