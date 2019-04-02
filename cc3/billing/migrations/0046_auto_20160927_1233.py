# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0045_billingsettings_twinfield_project_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceset',
            name='extras_generated_at',
            field=models.DateTimeField(null=True, verbose_name='Extra CSV Files generated at', blank=True),
        ),
        migrations.AlterField(
            model_name='invoicedatafile',
            name='file_type',
            field=models.CharField(default=b'invoices', max_length=10, verbose_name='File type', choices=[(b'products', b'products'), (b'users', b'users'), (b'invoices', b'invoices'), (b'extra_csv', b'extra_csv')]),
        ),
    ]
