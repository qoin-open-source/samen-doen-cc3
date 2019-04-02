# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import cc3.core.utils


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('cyclos', '0003_auto_20160609_1610'),
        ('rules', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileServiceUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ip_addresses', models.CharField(help_text='Optional list of ip4 ip addresses (comma delimited) where user can access service from', max_length=255, blank=True)),
                ('user', models.ForeignKey(to='cyclos.User')),
            ],
        ),
        migrations.CreateModel(
            name='FileType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(help_text='Description of the file type', max_length=255)),
                ('instance_identifier', models.CharField(default=b'', help_text='name of (heading) field in process_model to be used as identifier for get_or_create on import', max_length=255, blank=True)),
                ('clear_before_process', models.BooleanField(default=True, help_text='Empty temp table before uploading data from file?')),
                ('allow_duplicates', models.BooleanField(default=True, help_text='If True, duplicate instance sent to model.handle_duplicate() post creation')),
            ],
        ),
        migrations.CreateModel(
            name='FileTypeSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Name of group of file types which can be processed together', max_length=255, verbose_name='File Type Set')),
                ('email_addresses', models.TextField(default=b'', help_text='Email addresses (comma separated) where an Excel report should be sent', blank=True)),
                ('ruleset', models.ForeignKey(blank=True, to='rules.RuleSet', help_text='Which set of rules should be used to process these files', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='FileTypeSetRun',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rule_results', models.TextField()),
                ('filetypeset', models.ForeignKey(to='files.FileTypeSet')),
            ],
        ),
        migrations.CreateModel(
            name='Format',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(help_text='Description of the file format', max_length=255)),
                ('mime_type', models.CharField(help_text='Expected MIME type of the file', max_length=100)),
                ('extension', models.CharField(help_text='Expected file extension for type', max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Upload',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', models.FileField(max_length=500, upload_to=cc3.core.utils.UploadTo(b'uploaded_files', b'id'))),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date created')),
                ('status', models.CharField(default=b'Uploaded', max_length=10, verbose_name='Status', choices=[(b'Uploaded', 'Uploaded'), (b'Processed', 'Processed')])),
                ('file_type', models.ForeignKey(to='files.FileType')),
                ('user_created', models.ForeignKey(to='cyclos.User')),
            ],
        ),
        migrations.CreateModel(
            name='UploadInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField(editable=False)),
                ('status', models.CharField(default=b'Uploaded', max_length=10, verbose_name='Status', choices=[(b'Uploaded', 'Uploaded'), (b'Processed', 'Processed')])),
                ('content_type', models.ForeignKey(editable=False, to='contenttypes.ContentType')),
                ('upload', models.ForeignKey(editable=False, to='files.Upload')),
            ],
        ),
        migrations.AddField(
            model_name='filetype',
            name='filetypeset',
            field=models.ForeignKey(blank=True, to='files.FileTypeSet', null=True),
        ),
        migrations.AddField(
            model_name='filetype',
            name='format',
            field=models.ForeignKey(to='files.Format'),
        ),
        migrations.AddField(
            model_name='filetype',
            name='process_model',
            field=models.ForeignKey(blank=True, to='contenttypes.ContentType', help_text='If set, validate and if not testint, save data from file to model instances of this type', null=True),
        ),
    ]
