# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0003_auto_20160921_1628'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fulfillment',
            options={'ordering': ('-status', '-last_modified'), 'verbose_name': 'Fulfillment', 'verbose_name_plural': 'Fulfillments'},
        ),
        migrations.AddField(
            model_name='fulfillment',
            name='number',
            field=models.OneToOneField(null=True, verbose_name='Card', to='cards.Card'),
        ),
        migrations.AlterField(
            model_name='fulfillment',
            name='status',
            field=models.CharField(max_length=25, verbose_name='Status', choices=[(b'New', 'In Behandeling'), (b'Manually Processed', 'Manually Processed'), (b'Account Closed', 'Cancelled (Account closed)')]),
        ),
    ]
