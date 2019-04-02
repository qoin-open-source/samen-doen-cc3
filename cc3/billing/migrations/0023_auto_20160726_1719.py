# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0022_auto_20160720_1257'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoiceCSVFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file_type', models.CharField(default=b'invoices', max_length=10, verbose_name='File type', choices=[(b'products', b'products'), (b'users', b'users'), (b'invoices', b'invoices')])),
                ('generated_at', models.DateTimeField(null=True, blank=True)),
                ('csv_file', models.FileField(upload_to=b'billing/%Y/')),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('generated_at', models.DateTimeField(null=True, blank=True)),
                ('sent_at', models.DateTimeField(null=True, blank=True)),
                ('sent_to', models.TextField(blank=True)),
                ('invoices', models.ManyToManyField(related_name='invoiceset', verbose_name='Invoices', to='billing.Invoice')),
            ],
        ),
        migrations.AlterField(
            model_name='productpricing',
            name='type',
            field=models.CharField(default=b'UNIT', max_length=20, verbose_name='Price type', choices=[(b'UNIT', 'Unit price'), (b'TXN_UNIT', 'Per transaction charge'), (b'TXN_PERCENT', 'Transaction value percentage'), (b'TERM_UNIT', 'Per terminal charge'), (b'TERM_DEPOSIT', 'Terminal deposit')]),
        ),
        migrations.AddField(
            model_name='invoicecsvfile',
            name='invoice_set',
            field=models.ForeignKey(related_name='csv_files', verbose_name='Invoice set', to='billing.InvoiceSet'),
        ),
    ]
