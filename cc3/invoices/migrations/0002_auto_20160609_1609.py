# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0001_initial'),
        ('invoices', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='from_user',
            field=models.ForeignKey(related_name='invoices_from', default=1, to='cyclos.User'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='to_user',
            field=models.ForeignKey(related_name='invoices_to', default=1, to='cyclos.User'),
            preserve_default=False,
        ),
    ]
