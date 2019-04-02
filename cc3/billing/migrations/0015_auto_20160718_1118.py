# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0014_auto_20160714_1108'),
    ]

    operations = [
        migrations.AddField(
            model_name='productpricing',
            name='percentage_price',
            field=models.DecimalField(null=True, verbose_name='Percentage price', max_digits=5, decimal_places=2, blank=True),
        ),
        migrations.AddField(
            model_name='productpricing',
            name='type',
            field=models.CharField(default=b'UNIT', max_length=20, verbose_name='Price type', choices=[(b'UNIT', 'Unit price'), (b'TXN_UNIT', 'Per transaction charge'), (b'TXN_PERCENT', 'Transaction value percentage'), (b'TERM_UNIT', 'Per terminal charge'), (b'TERM_DEPOSIT', 'Terminal deposit')]),
        ),
        migrations.AlterField(
            model_name='taxregime',
            name='percent',
            field=models.DecimalField(null=True, verbose_name='% rate', max_digits=5, decimal_places=2, blank=True),
        ),
    ]
