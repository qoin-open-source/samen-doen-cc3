# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cmscontent', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='homepageblock',
            name='cmsplugin_ptr',
            field=models.OneToOneField(parent_link=True, related_name='cmscontent_homepageblock', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
        migrations.AlterField(
            model_name='homepageheader',
            name='cmsplugin_ptr',
            field=models.OneToOneField(parent_link=True, related_name='cmscontent_homepageheader', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
        migrations.AlterField(
            model_name='notificationplugin',
            name='cmsplugin_ptr',
            field=models.OneToOneField(parent_link=True, related_name='cmscontent_notificationplugin', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
        migrations.AlterField(
            model_name='sectioncarouselplugin',
            name='cmsplugin_ptr',
            field=models.OneToOneField(parent_link=True, related_name='cmscontent_sectioncarouselplugin', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
        migrations.AlterField(
            model_name='sectioncolumnnewsplugin',
            name='cmsplugin_ptr',
            field=models.OneToOneField(parent_link=True, related_name='cmscontent_sectioncolumnnewsplugin', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
        migrations.AlterField(
            model_name='sectioncolumnnoticeplugin',
            name='cmsplugin_ptr',
            field=models.OneToOneField(parent_link=True, related_name='cmscontent_sectioncolumnnoticeplugin', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
        migrations.AlterField(
            model_name='socialmedialinksplugin',
            name='cmsplugin_ptr',
            field=models.OneToOneField(parent_link=True, related_name='cmscontent_socialmedialinksplugin', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
    ]
