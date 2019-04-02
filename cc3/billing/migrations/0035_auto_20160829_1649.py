# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0034_auto_20160829_1505'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='article_code',
            field=models.CharField(default=b'VRK', max_length=20, verbose_name='Article code'),
        ),
        migrations.AlterField(
            model_name='product',
            name='subarticle_code',
            field=models.CharField(max_length=20, verbose_name='Sub-article code'),
        ),
        migrations.AlterUniqueTogether(
            name='product',
            unique_together=set([('article_code', 'subarticle_code')]),
        ),
    ]
