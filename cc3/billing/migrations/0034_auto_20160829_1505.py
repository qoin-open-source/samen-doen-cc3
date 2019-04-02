# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0033_auto_20160824_1446'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoiceDataFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file_type', models.CharField(default=b'invoices', max_length=10, verbose_name='File type', choices=[(b'products', b'products'), (b'users', b'users'), (b'invoices', b'invoices')])),
                ('generated_at', models.DateTimeField(null=True, blank=True)),
                ('data_file', models.FileField(upload_to=b'billing/%Y/')),
                ('invoice_set', models.ForeignKey(related_name='data_files', verbose_name='Invoice set', to='billing.InvoiceSet')),
            ],
        ),
        migrations.RemoveField(
            model_name='invoicecsvfile',
            name='invoice_set',
        ),
        migrations.AlterModelOptions(
            name='billingsettings',
            options={'verbose_name_plural': 'Billing Settings'},
        ),
        migrations.DeleteModel(
            name='InvoiceCSVFile',
        ),
    ]
