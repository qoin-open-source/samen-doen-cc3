import datetime

import json
import logging

from django.utils import timezone

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import dateparse
from django.utils.translation import ugettext_lazy as _

from .utils import str_to_class, last_month_first_of_month


LOG = logging.getLogger(__name__)

JOIN_CONDITIONS = (
    ('AND', 'AND'),
    ('OR', 'OR'),
)

OPERATOR_CHOICES = (
    ('==', _('equals')),
    ('>', _('greater than')),
    ('<', _('less than')),
    ('>=', _('greater than or equal to')),
    ('<=', _('less than or equal to')),
    ('!=', _('not equal to')),
    ('is', _('Use when comparing anything with (python) None (Python null)')),
)


class RuleSet(models.Model):
    """
    A collection of Rules which should be run in rule sequence order.
    """
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return u'%s' % self.name

    def run(self, instances_list):
        """
        Run all rules in this set.

        Instances from the list of instances are used according to which
        process_model the Rule uses
        :param instances_list:
        :return: list of rule ids that return True (up to exit_on_match)
        """
        rule_results = []

        def get_instance(list_of_instances, content_type):
            for _instance in list_of_instances:
                if isinstance(_instance, content_type.model_class()):
                    return _instance

        instance_identifier = None
        rules = Rule.objects.filter(ruleset=self, active=True).order_by(
            'sequence')
        instance = None

        for rule in rules:
            instance = get_instance(instances_list, rule.process_model)
            result = rule.run_evaluate(instance)
            if not instance_identifier:
                instance_identifier = rule.instance_identifier
            if result:
                rule_results.append({
                    "identity": getattr(instance, instance_identifier),
                    "result": result
                })
                if rule.exit_on_match:
                    return rule_results
            else:
                if rule.exit_on_fail:
                    return rule_results

        if not rule_results:
            rule_results = [{'identity': getattr(
                instance, instance_identifier), 'result': None}]
        return rule_results


class Rule(models.Model):
    """
    A set of conditions which evaluate to True or False.

    If True, then the action_class is instantiated, and the `perform` method
    called with the parameter_names and values.
    """
    name = models.CharField(
        max_length=150, blank=True, help_text=_(u"Name of rule"))
    description = models.CharField(
        max_length=255, blank=True, help_text=_("Description of rule"))
    ruleset = models.ForeignKey(
        'RuleSet', null=True, blank=True,
        help_text=_(u'Which set of rules does this belong to'))

    action_class = models.CharField(
        max_length=255, blank=True, default='',
        help_text=_(u"Action to be run (if any), ie: cc3.rules.actions.Pay"))
    parameter_names = models.CharField(
        max_length=255, blank=True, default='', help_text=_(u"Amount"))
    parameter_values = models.CharField(
        max_length=255, blank=True, default='', help_text=_(u"123"))

    process_model = models.ForeignKey(
        ContentType,
        help_text=_('Process model of instance passed to run_evaluate. Also '
                    'used to identify related rules'))

    instance_identifier = models.CharField(
        max_length=255,
        help_text=_(u"Instance identifier, which model instance field passed "
                    u"to run_evaluate should be handed over to action"))

    instance_qualifier = models.CharField(
        max_length=255,
        default='',
        blank=True,
        help_text=_("Extra kwargs as qualifier in case of multiple rows, for "
                    "example {'parent': None}")
    )

    # if evaluates as true, exit rules evaluation chain
    exit_on_match = models.BooleanField(
        default=False,
        help_text=_(u'If checked, exit rule chain if it evaluates true'))

    # if evaluates as false, exit rules evaluation chain
    exit_on_fail = models.BooleanField(
        default=False,
        help_text=_(u'If checked, exit rule chain if it evaluates false'))

    perform_action_once = models.BooleanField(
        default=False,
        help_text=_(u'If checked, only ever perform the action once'))

    # sequence to perform rules in
    sequence = models.IntegerField(
        help_text=_(u'Sequence in which to run rules'))

    active = models.BooleanField(
        default=True, help_text=_(u"Run rule as part of ruleset"))

    class Meta:
        ordering = ['sequence']

    def __unicode__(self):
        return self.name

    def run_evaluate(self, instance):
        """
        Where instance is an instance of the process_model ContentType

        Applies all conditions to (process) model instance. If conditions all
        match then fire action. A RuleStatus instance is created if evaluation
        takes place.

        When evaluating, if a Condition has an AND join type, and does not
        pass, then evaluation exits. If it is an OR type and does not pass then
        the next condition is evaluated; however if no conditions evaluate then
        no change of state will take place (for more complex AND/OR logic
        create more rule instances).
        """
        # return None if not true, or rule_status id if True (for reporting)?
        if not self.active:
            return

        hits = 0
        condition = None

        for condition in self.condition_set.all():
            result = condition.run_evaluate(instance)
            if result:
                hits += 1
            elif condition.join_condition == 'AND':
                return

        if hits == 0:
            return

        # what is the instances identity?
        identity = getattr(instance, self.instance_identifier)

        # check to see if action can be performed more than once
        if self.perform_action_once and self.rulestatus_set.filter(
                identity=identity,
                content_type=self.process_model).count() > 0:
            return

        # last condition is used to generate rule status
        rule_status, create = RuleStatus.objects.get_or_create(
            rule=self,
            condition=condition,
            content_type=self.process_model,
            object_id=instance.id,
            identity=identity
        )

        # Perform action - rule must have passed, and there must be an action
        # class if no action class, then obviously don't do anything, carry on
        # the ruleset sequence.
        if self.action_class:
            madule = self.action_class[:self.action_class.rindex(".")]
            klass = self.action_class[self.action_class.rindex(".") + 1:]
            action = str_to_class(madule, klass)

            # prepare kwargs
            parameters = self.parameter_names.split(",")
            values = self.parameter_values.split(",")
            kwargs = dict(zip(parameters, values))

            # add instance specific id
            kwargs[self.instance_identifier] = identity

            # hand over rule id, so that any rule field(s) can be used in
            # payment description
            kwargs['rule_id'] = self.id

            # perform action as rule passed, and no limit to
            performed_result = action.perform(**kwargs)
            ActionStatus.objects.get_or_create(
                action=self.action_class,
                rule_status=rule_status,
                performed=performed_result[:255]  # avoid overflow
            )

        return rule_status.id


class Condition(models.Model):
    """
    Rule condition, compares field on model specified in rule, according to
    operator, with an expression.

    The expression can be any python evaluable string. safeguards in place to
    limit to certain date and number builtins and locals.
    """

    rule = models.ForeignKey(Rule)
    evaluates_field = models.CharField(
        _('Field'),
        max_length=255,
        help_text=_(u"Name of (heading for) field in rule process_model where "
                    u"to get value for condition"))
    field_expression = models.TextField(
        _('Field Expression'),
        blank=True,
        default='',
        help_text=_(u"If the field needs to be a parameter of an expression, "
                    u"use expression({0}) where {0} will be replaced with the "
                    u"field value, ie dateparse.parse_datetime('{0}').month"))
    evaluate_operator = models.CharField(
        _('Operator'),
        max_length=10,
        choices=OPERATOR_CHOICES,
        default=OPERATOR_CHOICES[0][0],  # '=='
        help_text=_(u'Operator to use for condition, field operator '
                    u'expression, ie price > (10*1.04)+4'))

    # Maybe add optional field and models for r.h. side of condition?
    evaluate_expression = models.TextField(
        _('Expression'),
        help_text=_(u"(Python) expression for condition to evaluate and "
                    u"compare with, ie (125*1.05) or timezone.now().month"))

    # AND or OR (see Rule)
    join_condition = models.CharField(
        max_length=3, choices=JOIN_CONDITIONS, default='AND')

    def __unicode__(self):
        text = [self.join_condition, "IF", self.rule.process_model.name,
                self.evaluates_field, self.evaluate_operator,
                self.evaluate_expression]
        return " ".join(text)

    def run_evaluate(self, instance):
        value = process_model_instance = None
        process_model = self.rule.process_model

        try:
            instance_identifier = self.rule.instance_identifier
            instance_qualifier = self.rule.instance_qualifier
            kwargs = {instance_identifier: getattr(
                instance, instance_identifier)}
            if instance_qualifier:
                extra_dict = json.loads(instance_qualifier)
                kwargs = dict(kwargs, **extra_dict)
            process_model_instance = process_model.model_class().objects.get(
                **kwargs)
        except Exception, e:
            LOG.error("Error in condition {0}: {1}".format(
                self.__unicode__(), e))
            return False

        # make a list of safe functions:
        # http://lybniz2.sourceforge.net/safeeval.html
        safe_list = [choice[0] for choice in OPERATOR_CHOICES] + \
                    ['*', '+', '-', '/']  # , 'datetime']
        # , ''
        #    'math','acos', 'asin', 'atan', 'atan2', 'ceil', 'cos',
        #    'cosh', 'degrees', 'e', 'exp', 'fabs',
        #    'floor', 'fmod', 'frexp', 'hypot', 'ldexp', 'log', 'log10',
        #    'modf', 'pi', 'pow', 'radians', 'sin',
        #    'sinh', 'sqrt', 'tan', 'tanh'
        # ]

        #        #use the list to filter the local namespace
        safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
        #
        #        #add any needed builtins back in.
        safe_dict['dateparse'] = dateparse
        safe_dict['timezone'] = timezone
        safe_dict['timedelta'] = datetime.timedelta
        safe_dict['date'] = datetime.date
        safe_dict['last_month_first_of_month'] = last_month_first_of_month

        # get value of field from ORM
        value = getattr(process_model_instance, self.evaluates_field)

        # add value into safe dict
        safe_dict['value'] = value

        # check if value is raw or needs an eval
        if self.field_expression:
            # field value then needs to replace {0} in field_expression, and
            # then be evaluated.
            value_func = self.field_expression.format(value)
            value = eval(value_func, {"__builtins__": None}, safe_dict)

        if isinstance(value, datetime.datetime):
            condition_func = "dateparse.parse_datetime('{0}') {1} {2}".format(
                value, self.evaluate_operator, self.evaluate_expression)
        elif isinstance(value, datetime.date):
            condition_func = "dateparse.parse_date('{0}') {1} {2}".format(
                value, self.evaluate_operator, self.evaluate_expression)
        elif isinstance(value, unicode):
            condition_func = u"'{0}' {1} '{2}'".format(
                value, self.evaluate_operator, self.evaluate_expression)
        else:
            condition_func = "{0} {1} {2}".format(
                value, self.evaluate_operator, self.evaluate_expression)

        LOG.debug(u"condition evaluates: {0}".format(condition_func))
        return_value = eval(condition_func, {"__builtins__": None}, safe_dict)
        LOG.debug(u"condition returns: {0}".format(return_value))

        return return_value


class RuleStatus(models.Model):
    rule = models.ForeignKey(Rule)
    condition = models.ForeignKey(Condition)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    identity = models.CharField(
        max_length=255,
        default="-1",
        blank=True,
        help_text=_(u"What value was in the instance_identifier field, ie "
                    u"which persoonnummer?"))

    class Meta:
        verbose_name_plural = 'Rule status'

    def __unicode__(self):
        return u"Condition {0} on rule {1}".format(
            unicode(self.condition), unicode(self.rule))


class ActionStatus(models.Model):
    action = models.CharField(
        max_length=255, help_text=_("Which action was performed"))
    params = models.CharField(
        max_length=255, help_text=_("What parameters were passed"))
    rule_status = models.ForeignKey(
        RuleStatus,
        help_text=_("Which RuleStatus caused this action to be run"))
    performed = models.CharField(
        max_length=255, help_text=_("What did the action return"))

    class Meta:
        verbose_name_plural = 'Action status'

    def __unicode__(self):
        return u"{0} ({1}), {2}, {3}".format(
            self.action, self.performed, self.rule_status, self.performed)
