# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models, connection


class Migration(SchemaMigration):

    def forwards(self, orm):
        table_names = connection.introspection.table_names()

        # EXAMPLE FROM DjangoCMS File plugin.
        # NB only implementing forward migration where table exists, and
        # database table is to be renamed in line with normal django app model
        # table naming - ie cmscontent_<pluginname> .

        # The 'create' migration will need to be made when moving to Django 1.8
        # if 'cmsplugin_file' in table_names:
        #     db.rename_table('cmsplugin_file', 'djangocms_file_file')
        # elif 'file_file' in table_names:
        #     db.rename_table('file_file', 'djangocms_file_file')
        # else:
        #     # Adding model 'File'
        #     db.create_table(u'djangocms_file_file', (
        #         (u'cmsplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['cms.CMSPlugin'], unique=True, primary_key=True)),
        #         ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        #         ('title', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        #     ))

        if 'cmsplugin_notificationplugin' in table_names:
            db.rename_table('cmsplugin_notificationplugin', 'cmscontent_notificationplugin')
            db.send_create_signal(u'cmscontent_notificationplugin', ['NotificationPlugin'])

        if 'cmsplugin_homepageblock' in table_names:
            db.rename_table('cmsplugin_homepageblock', 'cmscontent_homepageblock')
            db.send_create_signal(u'cmscontent_homepageblock', ['HomepageBlock'])

        if 'cmsplugin_homepageheader' in table_names:
            db.rename_table('cmsplugin_homepageheader', 'cmscontent_homepageheader')
            db.send_create_signal(u'cmscontent_homepageheader', ['HomepageHeader'])

        if 'cmsplugin_sectioncarouselplugin' in table_names:
            db.rename_table('cmsplugin_sectioncarouselplugin', 'cmscontent_sectioncarouselplugin')
            db.send_create_signal(u'cmscontent_sectioncarouselplugin', ['SectionCarouselPlugin'])

        if 'cmsplugin_sectioncolumnnewsplugin' in table_names:
            db.rename_table('cmsplugin_sectioncolumnnewsplugin', 'cmscontent_sectioncolumnnewsplugin')
            db.send_create_signal(u'cmscontent_sectioncolumnnewsplugin', ['SectionColumnNewsPlugin'])

        if 'cmsplugin_sectioncolumnnoticeplugin' in table_names:
            db.rename_table('cmsplugin_sectioncolumnnoticeplugin', 'cmscontent_sectioncolumnnoticeplugin')
            db.send_create_signal(u'cmscontent_sectioncolumnnoticeplugin', ['SectionColumnNoticePlugin'])

        if 'cmsplugin_socialmedialinksplugin' in table_names:
            db.rename_table('cmsplugin_socialmedialinksplugin', 'cmscontent_socialmedialinksplugin')
            db.send_create_signal(u'cmscontent_socialmedialinksplugin', ['SocialMediaLinksPlugin'])

    def backwards(self, orm):
        # Deleting model 'NotificationPlugin'
        db.delete_table(u'cmscontent_notificationplugin')
        db.delete_table(u'cmscontent_homepageblock')
        db.delete_table(u'cmscontent_homepageheader')
        db.delete_table(u'cmscontent_sectioncarouselplugin')
        db.delete_table(u'cmscontent_sectioncolumnnewsplugin')
        db.delete_table(u'cmscontent_sectioncolumnnoticeplugin')
        db.delete_table(u'cmscontent_socialmedialinksplugin')

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'changed_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '15', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        u'cmscontent.cmsplaceholder': {
            'Meta': {'ordering': "('page_identifier',)", 'object_name': 'CMSPlaceholder'},
            'cmscontent_placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'page_identifier': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'cmscontent.homepageblock': {
            'Meta': {'ordering': "('creation_date', 'title')", 'object_name': 'HomepageBlock', '_ormbases': ['cms.CMSPlugin']},
            'block_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'icon': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'sub_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'cmscontent.homepageheader': {
            'Meta': {'ordering': "('creation_date', 'title')", 'object_name': 'HomepageHeader', '_ormbases': ['cms.CMSPlugin']},
            'button_link_text': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'header_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'paragraph': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'cmscontent.newsentry': {
            'Meta': {'ordering': "('title', 'created_by')", 'object_name': 'NewsEntry'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': "'title'"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        u'cmscontent.notificationplugin': {
            'Meta': {'ordering': "('creation_date',)", 'object_name': 'NotificationPlugin', '_ormbases': ['cms.CMSPlugin']},
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'info_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'notice': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'notification_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'notification_link_label': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'notification_type': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'})
        },
        u'cmscontent.sectioncarouselplugin': {
            'Meta': {'object_name': 'SectionCarouselPlugin', '_ormbases': ['cms.CMSPlugin']},
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'carousel'", 'max_length': '75'})
        },
        u'cmscontent.sectioncarouselpluginslide': {
            'Meta': {'ordering': "('title_line_1',)", 'object_name': 'SectionCarouselPluginSlide'},
            'carousel': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['cmscontent.SectionCarouselPlugin']"}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'image_alt': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '75', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title_line_1': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'title_line_2': ('django.db.models.fields.CharField', [], {'max_length': '75'})
        },
        u'cmscontent.sectioncolumnnewsplugin': {
            'Meta': {'ordering': "('title',)", 'object_name': 'SectionColumnNewsPlugin', '_ormbases': ['cms.CMSPlugin']},
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'num_entries': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        u'cmscontent.sectioncolumnnoticeplugin': {
            'Meta': {'object_name': 'SectionColumnNoticePlugin', '_ormbases': ['cms.CMSPlugin']},
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'link_target': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'link_text': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'paragraph_1': ('django.db.models.fields.TextField', [], {}),
            'paragraph_2': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'})
        },
        u'cmscontent.socialmedialink': {
            'Meta': {'object_name': 'SocialMediaLink'},
            'css_icon_class': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_target': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'link_text': ('django.db.models.fields.CharField', [], {'max_length': '130', 'blank': 'True'}),
            'social_plugin': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['cmscontent.SocialMediaLinksPlugin']"})
        },
        u'cmscontent.socialmedialinksplugin': {
            'Meta': {'object_name': 'SocialMediaLinksPlugin', '_ormbases': ['cms.CMSPlugin']},
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'social media'", 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['cmscontent']
