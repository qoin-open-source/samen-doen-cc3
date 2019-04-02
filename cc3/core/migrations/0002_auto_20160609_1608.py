# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import adminsortable.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='receiver',
            field=models.ForeignKey(related_name='payment_receiver', to='cyclos.User'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='sender',
            field=models.ForeignKey(related_name='payment_sender', to='cyclos.User'),
        ),
        migrations.AddField(
            model_name='trackedprofilecategory',
            name='category',
            field=models.ForeignKey(to='core.Category'),
        ),
        migrations.AddField(
            model_name='trackedprofilecategory',
            name='profile',
            field=models.ForeignKey(to='cyclos.CC3Profile'),
        ),
        migrations.AddField(
            model_name='categorytranslation',
            name='category',
            field=models.ForeignKey(blank=True, to='core.Category', null=True),
        ),
        migrations.AddField(
            model_name='category',
            name='parent',
            field=adminsortable.fields.SortableForeignKey(related_name='children', blank=True, to='core.Category', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='categorytranslation',
            unique_together=set([('language', 'category')]),
        ),
    ]
