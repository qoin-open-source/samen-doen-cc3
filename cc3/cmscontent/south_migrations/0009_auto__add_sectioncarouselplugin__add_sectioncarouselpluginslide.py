# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SectionCarouselPlugin'
        db.create_table(u'cmsplugin_sectioncarouselplugin', (
            (u'cmsplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['cms.CMSPlugin'], unique=True, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default='carousel', max_length=75)),
        ))
        db.send_create_signal(u'cmscontent', ['SectionCarouselPlugin'])

        # Adding model 'SectionCarouselPluginSlide'
        db.create_table(u'cmscontent_sectioncarouselpluginslide', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('carousel', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cmscontent.SectionCarouselPlugin'])),
            ('date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('title_line_1', self.gf('django.db.models.fields.CharField')(max_length=75)),
            ('title_line_2', self.gf('django.db.models.fields.CharField')(max_length=75)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('image_alt', self.gf('django.db.models.fields.CharField')(default='', max_length=75)),
        ))
        db.send_create_signal(u'cmscontent', ['SectionCarouselPluginSlide'])


    def backwards(self, orm):
        # Deleting model 'SectionCarouselPlugin'
        db.delete_table(u'cmsplugin_sectioncarouselplugin')

        # Deleting model 'SectionCarouselPluginSlide'
        db.delete_table(u'cmscontent_sectioncarouselpluginslide')


    models = {
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
            'Meta': {'ordering': "('creation_date', 'title')", 'object_name': 'HomepageBlock', 'db_table': "u'cmsplugin_homepageblock'", '_ormbases': ['cms.CMSPlugin']},
            'block_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'icon': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'sub_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'cmscontent.homepageheader': {
            'Meta': {'ordering': "('creation_date', 'title')", 'object_name': 'HomepageHeader', 'db_table': "u'cmsplugin_homepageheader'", '_ormbases': ['cms.CMSPlugin']},
            'button_link_text': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'header_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'paragraph': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'cmscontent.notificationplugin': {
            'Meta': {'ordering': "('creation_date',)", 'object_name': 'NotificationPlugin', 'db_table': "u'cmsplugin_notificationplugin'", '_ormbases': ['cms.CMSPlugin']},
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'info_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'notice': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'notification_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'notification_link_label': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'notification_type': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'})
        },
        u'cmscontent.sectioncarouselplugin': {
            'Meta': {'object_name': 'SectionCarouselPlugin', 'db_table': "u'cmsplugin_sectioncarouselplugin'", '_ormbases': ['cms.CMSPlugin']},
            u'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'carousel'", 'max_length': '75'})
        },
        u'cmscontent.sectioncarouselpluginslide': {
            'Meta': {'ordering': "('title_line_1',)", 'object_name': 'SectionCarouselPluginSlide'},
            'carousel': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['cmscontent.SectionCarouselPlugin']"}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'image_alt': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '75'}),
            'title_line_1': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'title_line_2': ('django.db.models.fields.CharField', [], {'max_length': '75'})
        }
    }

    complete_apps = ['cmscontent']