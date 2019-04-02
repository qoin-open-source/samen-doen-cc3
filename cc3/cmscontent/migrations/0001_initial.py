# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import autoslug.fields
import cms.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cyclos', '0005_auto_20160616_1053'),
        ('cms', '0015_auto_20160421_0000'),
    ]

    operations = [
        migrations.CreateModel(
            name='CMSPlaceholder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('page_identifier', models.CharField(unique=True, max_length=255, choices=[(b'accounts_add_funds', b'accounts_add_funds'), (b'accounts_credit_eligibility_criterea', b'accounts_credit_eligibility_criterea'), (b'accounts_credit_application_procedure', b'accounts_credit_application_procedure'), (b'accounts_credit_review', b'accounts_credit_review'), (b'accounts_credit_further_questions', b'accounts_credit_further_questions'), (b'accounts_apply_for_upgrade', b'accounts_apply_for_upgrade'), (b'accounts_apply_for_upgrade_below_form', b'accounts_apply_for_upgrade_below_form'), (b'registration_password_reset', b'registration_password_reset'), (b'registration_login_message', b'registration_login_message'), (b'accounts_exchange_to_money', b'accounts_exchange_to_money')])),
                ('cmscontent_placeholder', cms.models.fields.PlaceholderField(slotname=b'cmscontent_placeholder', editable=False, to='cms.Placeholder', null=True)),
            ],
            options={
                'ordering': ('page_identifier',),
            },
        ),
        migrations.CreateModel(
            name='HomepageBlock',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('title', models.CharField(max_length=100)),
                ('sub_title', models.CharField(max_length=100, blank=True)),
                ('block_link', models.CharField(max_length=255, blank=True)),
                ('icon', models.CharField(blank=True, max_length=100, choices=[(b'icon_1', b'Business'), (b'icon_2', b'Policy maker'), (b'icon_3', b'Communities'), (b'icon_4', b'Folder')])),
            ],
            options={
                'ordering': ('creation_date', 'title'),
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='HomepageHeader',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('title', models.CharField(max_length=100)),
                ('paragraph', models.TextField()),
                ('header_link', models.URLField(null=True, blank=True)),
                ('button_link_text', models.CharField(max_length=20, null=True, blank=True)),
            ],
            options={
                'ordering': ('creation_date', 'title'),
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='NewsEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True, verbose_name='creation Date')),
                ('title', models.CharField(max_length=150, verbose_name='title')),
                ('content', models.TextField(verbose_name='content')),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'title', editable=False)),
                ('created_by', models.ForeignKey(verbose_name='created by', to='cyclos.User')),
            ],
            options={
                'ordering': ('title', 'created_by'),
                'verbose_name': 'News entry',
                'verbose_name_plural': 'News entries',
            },
        ),
        migrations.CreateModel(
            name='NotificationPlugin',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('notification_type', models.SmallIntegerField(default=1, choices=[(1, 'Near event'), (2, 'Alert'), (3, 'Information')])),
                ('date', models.DateTimeField(null=True, blank=True)),
                ('notice', models.CharField(max_length=100)),
                ('info_link', models.URLField(null=True, blank=True)),
                ('notification_link', models.URLField(null=True, blank=True)),
                ('notification_link_label', models.CharField(max_length=20, null=True, blank=True)),
            ],
            options={
                'ordering': ('creation_date',),
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='SectionCarouselPlugin',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('name', models.CharField(default=b'carousel', max_length=75, verbose_name='name')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='SectionCarouselPluginSlide',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(null=True, blank=True)),
                ('title_line_1', models.CharField(max_length=75, verbose_name='title line 1')),
                ('title_line_2', models.CharField(max_length=75, verbose_name='title line 2')),
                ('image', models.ImageField(upload_to=b'cms_page_media/', verbose_name='image')),
                ('image_alt', models.CharField(default=b'', max_length=75, verbose_name='image alt', blank=True)),
                ('order', models.IntegerField(default=0)),
                ('carousel', models.ForeignKey(to='cmscontent.SectionCarouselPlugin')),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='SectionColumnNewsPlugin',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('title', models.CharField(max_length=150, verbose_name='title')),
                ('num_entries', models.IntegerField(default=3)),
            ],
            options={
                'ordering': ('title',),
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='SectionColumnNoticePlugin',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('title', models.CharField(default=b'', max_length=50, verbose_name='title')),
                ('paragraph_1', models.TextField()),
                ('paragraph_2', models.TextField()),
                ('link_target', models.URLField(null=True, blank=True)),
                ('link_text', models.CharField(max_length=50, null=True, verbose_name='link text', blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='SocialMediaLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('link_target', models.URLField()),
                ('link_text', models.CharField(max_length=130, blank=True)),
                ('css_icon_class', models.CharField(max_length=250, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='SocialMediaLinksPlugin',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('name', models.CharField(default=b'social media', max_length=75, verbose_name='name')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.AddField(
            model_name='socialmedialink',
            name='social_plugin',
            field=models.ForeignKey(to='cmscontent.SocialMediaLinksPlugin'),
        ),
    ]
