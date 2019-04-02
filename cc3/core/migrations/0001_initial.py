# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=1, editable=False, db_index=True)),
                ('title', models.CharField(help_text='Category title', max_length=100)),
                ('description', models.CharField(help_text='Category description', max_length=255)),
                ('active', models.BooleanField(default=True, help_text='Marks this Category as active')),
                ('ignore_for_matching', models.BooleanField(default=False, help_text="Don't report matching wants/offers for this Category")),
            ],
            options={
                'ordering': ('order', 'title'),
                'abstract': False,
                'verbose_name_plural': 'categories',
            },
        ),
        migrations.CreateModel(
            name='CategoryTranslation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Category title', max_length=50)),
                ('description', models.CharField(max_length=255)),
                ('language', models.CharField(max_length=5, choices=[(b'nl', b'Dutch')])),
            ],
        ),
        migrations.CreateModel(
            name='TrackedProfileCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category_type', models.CharField(max_length=5, choices=[(b'offer', b'Offer'), (b'want', b'Want')])),
                ('time_added', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date created')),
                ('transfer_id', models.IntegerField(default=0, help_text='Cyclos transaction ID - can be used for chargeback')),
                ('report_date', models.DateTimeField(null=True, verbose_name='Report date', blank=True)),
            ],
        ),
    ]
