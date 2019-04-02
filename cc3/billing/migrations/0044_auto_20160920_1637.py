# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0043_auto_20160919_1634'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='billingsettings',
            name='TWINFIELD_GL_ACCOUNT',
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='TWINFIELD_EMAIL_FILES_TO',
            field=models.CharField(default=b'', help_text='Email address(es), comma separated if more than one', max_length=200, verbose_name='Mail Twinfield data files to', blank=True),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='TWINFIELD_GL_ACCOUNT_PRODUCTS',
            field=models.CharField(default=b'8000', max_length=20, verbose_name='Twinfield GL account for Products'),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='TWINFIELD_GL_ACCOUNT_USERS',
            field=models.CharField(default=b'1300', max_length=20, verbose_name='Twinfield GL account for Users'),
        ),
    ]
