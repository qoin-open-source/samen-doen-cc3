# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActionStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action', models.CharField(help_text='Which action was performed', max_length=255)),
                ('params', models.CharField(help_text='What parameters were passed', max_length=255)),
                ('performed', models.CharField(help_text='What did the action return', max_length=255)),
            ],
            options={
                'verbose_name_plural': 'Action status',
            },
        ),
        migrations.CreateModel(
            name='Condition',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('evaluates_field', models.CharField(help_text='Name of (heading for) field in rule process_model where to get value for condition', max_length=255, verbose_name='Field')),
                ('field_expression', models.TextField(default=b'', help_text="If the field needs to be a parameter of an expression, use expression({0}) where {0} will be replaced with the field value, ie dateparse.parse_datetime('{0}').month", verbose_name='Field Expression', blank=True)),
                ('evaluate_operator', models.CharField(default=b'==', help_text='Operator to use for condition, field operator expression, ie price > (10*1.04)+4', max_length=10, verbose_name='Operator', choices=[(b'==', 'equals'), (b'>', 'greater than'), (b'<', 'less than'), (b'>=', 'greater than or equal to'), (b'<=', 'less than or equal to'), (b'!=', 'not equal to'), (b'is', 'Use when comparing anything with (python) None (Python null)')])),
                ('evaluate_expression', models.TextField(help_text='(Python) expression for condition to evaluate and compare with, ie (125*1.05) or timezone.now().month', verbose_name='Expression')),
                ('join_condition', models.CharField(default=b'AND', max_length=3, choices=[(b'AND', b'AND'), (b'OR', b'OR')])),
            ],
        ),
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Name of rule', max_length=150, blank=True)),
                ('description', models.CharField(help_text='Description of rule', max_length=255, blank=True)),
                ('action_class', models.CharField(default=b'', help_text='Action to be run (if any), ie: cc3.rules.actions.Pay', max_length=255, blank=True)),
                ('parameter_names', models.CharField(default=b'', help_text='Amount', max_length=255, blank=True)),
                ('parameter_values', models.CharField(default=b'', help_text='123', max_length=255, blank=True)),
                ('instance_identifier', models.CharField(help_text='Instance identifier, which model instance field passed to run_evaluate should be handed over to action', max_length=255)),
                ('instance_qualifier', models.CharField(default=b'', help_text="Extra kwargs as qualifier in case of multiple rows, for example {'parent': None}", max_length=255, blank=True)),
                ('exit_on_match', models.BooleanField(default=False, help_text='If checked, exit rule chain if it evaluates true')),
                ('exit_on_fail', models.BooleanField(default=False, help_text='If checked, exit rule chain if it evaluates false')),
                ('perform_action_once', models.BooleanField(default=False, help_text='If checked, only ever perform the action once')),
                ('sequence', models.IntegerField(help_text='Sequence in which to run rules')),
                ('active', models.BooleanField(default=True, help_text='Run rule as part of ruleset')),
                ('process_model', models.ForeignKey(help_text='Process model of instance passed to run_evaluate. Also used to identify related rules', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ['sequence'],
            },
        ),
        migrations.CreateModel(
            name='RuleSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='RuleStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('identity', models.CharField(default=b'-1', help_text='What value was in the instance_identifier field, ie which persoonnummer?', max_length=255, blank=True)),
                ('condition', models.ForeignKey(to='rules.Condition')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('rule', models.ForeignKey(to='rules.Rule')),
            ],
            options={
                'verbose_name_plural': 'Rule status',
            },
        ),
        migrations.AddField(
            model_name='rule',
            name='ruleset',
            field=models.ForeignKey(blank=True, to='rules.RuleSet', help_text='Which set of rules does this belong to', null=True),
        ),
        migrations.AddField(
            model_name='condition',
            name='rule',
            field=models.ForeignKey(to='rules.Rule'),
        ),
        migrations.AddField(
            model_name='actionstatus',
            name='rule_status',
            field=models.ForeignKey(help_text='Which RuleStatus caused this action to be run', to='rules.RuleStatus'),
        ),
    ]
