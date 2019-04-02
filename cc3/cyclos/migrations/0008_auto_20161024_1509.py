# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0007_cyclosgroup_initial_products'),
    ]

    operations = [
        migrations.AddField(
            model_name='cc3community',
            name='default_reward_percent',
            field=models.IntegerField(default=40, verbose_name='Default reward percentage', choices=[(0, b'0%'), (10, b'10%'), (20, b'20%'), (30, b'30%'), (40, b'40%'), (50, b'50%'), (60, b'60%'), (70, b'70%'), (80, b'80%'), (90, b'90%'), (100, b'100%')]),
        ),
        migrations.AddField(
            model_name='cc3community',
            name='max_reward_percent',
            field=models.IntegerField(default=40, verbose_name='Maximum reward percentage', choices=[(0, b'0%'), (10, b'10%'), (20, b'20%'), (30, b'30%'), (40, b'40%'), (50, b'50%'), (60, b'60%'), (70, b'70%'), (80, b'80%'), (90, b'90%'), (100, b'100%')]),
        ),
        migrations.AddField(
            model_name='cc3community',
            name='min_reward_percent',
            field=models.IntegerField(default=40, verbose_name='Minimum reward percentage', choices=[(0, b'0%'), (10, b'10%'), (20, b'20%'), (30, b'30%'), (40, b'40%'), (50, b'50%'), (60, b'60%'), (70, b'70%'), (80, b'80%'), (90, b'90%'), (100, b'100%')]),
        ),
    ]
