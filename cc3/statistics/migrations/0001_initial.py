# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Dashboard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Focus of statistics area', max_length=64)),
                ('sequence', models.IntegerField(help_text='Order of dashboards')),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['sequence'],
                'verbose_name': 'Dashboard',
                'verbose_name_plural': 'Dashboard',
            },
        ),
        migrations.CreateModel(
            name='Graph',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Title of the graph', max_length=255)),
                ('active', models.BooleanField(default=True)),
                ('sequence', models.IntegerField(help_text='Placement in dashboard of graphs')),
                ('raw_sql', models.TextField(default=b'', help_text='SQL to run to collect data for graph', blank=True)),
                ('sql_key', models.CharField(default=b'', help_text='Key identifying SQL to run to collect data for graph (only used if no Raw SQL supplied)', max_length=50, blank=True)),
                ('use_cyclos_database', models.BooleanField(default=False, help_text='When set to true, raw_sql is run against the cyclos database')),
                ('graph_type', models.CharField(default=b'', help_text='Graph type or leave blank', max_length=1, blank=True, choices=[(b'T', 'Table'), (b'B', 'Bar Graph'), (b'M', 'Multi Bar Graph')])),
                ('width', models.IntegerField(default=300, help_text='Width of graph on page')),
                ('height', models.IntegerField(default=400, help_text='Height of graph on page')),
                ('x_type', models.CharField(default=b'', help_text='Special treatment for x values, or leave blank', max_length=12, blank=True, choices=[(b'DATE_YM', "Year and month ('YYYYMM')")])),
                ('x_output_format', models.CharField(default=b'', help_text='Output format for x values (depending on x type), or leave blank', max_length=50, blank=True)),
                ('x_max_columns', models.IntegerField(help_text='Limit the number of x columns shown', null=True, blank=True)),
                ('table_add_totals_row', models.BooleanField(default=False, help_text="Add a 'Totals' row to table")),
                ('dashboard', models.ForeignKey(to='statistics.Dashboard')),
            ],
            options={
                'ordering': ['sequence'],
            },
        ),
    ]
