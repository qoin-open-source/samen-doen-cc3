# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('job_title', models.CharField(max_length=255)),
                ('member_email', models.CharField(max_length=75)),
                ('business_name', models.CharField(max_length=255)),
                ('company_website', models.CharField(max_length=255)),
                ('count_offers', models.IntegerField()),
                ('count_wants', models.IntegerField()),
                ('has_full_account', models.BooleanField()),
                ('count_active_ads', models.IntegerField()),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'managed': False,
            },
        ),
    ]
