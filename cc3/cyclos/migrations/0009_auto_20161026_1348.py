# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0008_auto_20161024_1509'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cc3community',
            name='default_reward_percent',
        ),
        migrations.RemoveField(
            model_name='cc3community',
            name='max_reward_percent',
        ),
        migrations.RemoveField(
            model_name='cc3community',
            name='min_reward_percent',
        ),
        migrations.AddField(
            model_name='cc3community',
            name='default_donation_percent',
            field=models.IntegerField(default=40, verbose_name='Default donation percentage', choices=[(0, b'0%'), (10, b'10%'), (20, b'20%'), (30, b'30%'), (40, b'40%'), (50, b'50%'), (60, b'60%'), (70, b'70%'), (80, b'80%'), (90, b'90%'), (100, b'100%')]),
        ),
        migrations.AddField(
            model_name='cc3community',
            name='max_donation_percent',
            field=models.IntegerField(default=40, verbose_name='Maximum donation percentage', choices=[(0, b'0%'), (10, b'10%'), (20, b'20%'), (30, b'30%'), (40, b'40%'), (50, b'50%'), (60, b'60%'), (70, b'70%'), (80, b'80%'), (90, b'90%'), (100, b'100%')]),
        ),
        migrations.AddField(
            model_name='cc3community',
            name='min_donation_percent',
            field=models.IntegerField(default=40, verbose_name='Minimum donation percentage', choices=[(0, b'0%'), (10, b'10%'), (20, b'20%'), (30, b'30%'), (40, b'40%'), (50, b'50%'), (60, b'60%'), (70, b'70%'), (80, b'80%'), (90, b'90%'), (100, b'100%')]),
        ),
    ]
