# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BulkPurchase'
        db.create_table(u'prizedraw_bulkpurchase', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('num_tickets', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('purchased_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='prizedraw_bulk_purchases', to=orm['auth.User'])),
            ('when_purchased', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('draw', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['prizedraw.Draw'])),
        ))
        db.send_create_signal(u'prizedraw', ['BulkPurchase'])

        # Adding model 'BulkPurchaseTicket'
        db.create_table(u'prizedraw_bulkpurchaseticket', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ticket', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['prizedraw.Ticket'])),
            ('bulk_purchase', self.gf('django.db.models.fields.related.ForeignKey')(related_name='bulk_purchase_tickets', to=orm['prizedraw.BulkPurchase'])),
        ))
        db.send_create_signal(u'prizedraw', ['BulkPurchaseTicket'])


    def backwards(self, orm):
        # Deleting model 'BulkPurchase'
        db.delete_table(u'prizedraw_bulkpurchase')

        # Deleting model 'BulkPurchaseTicket'
        db.delete_table(u'prizedraw_bulkpurchaseticket')


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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'prizedraw.bulkpurchase': {
            'Meta': {'object_name': 'BulkPurchase'},
            'draw': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['prizedraw.Draw']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tickets': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'purchased_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'prizedraw_bulk_purchases'", 'to': u"orm['auth.User']"}),
            'when_purchased': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        u'prizedraw.bulkpurchaseticket': {
            'Meta': {'object_name': 'BulkPurchaseTicket'},
            'bulk_purchase': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bulk_purchase_tickets'", 'to': u"orm['prizedraw.BulkPurchase']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ticket': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['prizedraw.Ticket']"})
        },
        u'prizedraw.draw': {
            'Meta': {'ordering': "('-draw_ends',)", 'object_name': 'Draw'},
            '_draw_number': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'draw_ends': ('django.db.models.fields.DateTimeField', [], {}),
            'draw_starts': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_tickets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1000000'}),
            'max_tickets_per_person': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10'}),
            'ticket_price': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'})
        },
        u'prizedraw.prize': {
            'Meta': {'ordering': "('-percentage_of_take', '-absolute_amount')", 'object_name': 'Prize'},
            'absolute_amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '8', 'decimal_places': '2', 'blank': 'True'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '8', 'decimal_places': '2', 'blank': 'True'}),
            'date_paid': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'draw': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'prizes'", 'to': u"orm['prizedraw.Draw']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'paid_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'percentage_of_take': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'winning_ticket': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prizes'", 'null': 'True', 'to': u"orm['prizedraw.Ticket']"})
        },
        u'prizedraw.repeatpurchase': {
            'Meta': {'object_name': 'RepeatPurchase'},
            'cancelled_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_months': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'num_tickets': ('django.db.models.fields.IntegerField', [], {}),
            'purchased_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prizedraw_repeat_purchases'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'when_purchased': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        u'prizedraw.repeatpurchaseticket': {
            'Meta': {'object_name': 'RepeatPurchaseTicket'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recurring_purchase': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'repeat_purchase_tickets'", 'to': u"orm['prizedraw.RepeatPurchase']"}),
            'ticket': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['prizedraw.Ticket']"})
        },
        u'prizedraw.ticket': {
            'Meta': {'unique_together': "(('draw', 'serial_number'),)", 'object_name': 'Ticket'},
            'draw': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tickets'", 'to': u"orm['prizedraw.Draw']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'purchase_transfer_id': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'purchased_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prizedraw_tickets'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'serial_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'when_purchased': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        }
    }

    complete_apps = ['prizedraw']