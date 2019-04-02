# encoding: utf-8

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from cc3.cyclos.tests.test_factories import CC3ProfileFactory
from cc3.cyclos.models.account import User

from .test_factories import RuleFactory, ConditionFactory


class RuleTests(TestCase):
    def setUp(self):
        #        self.backend = DummyCyclosBackend()
        #        set_backend(self.backend)

        # Create a user that act as instance for rule evaluation, and be passed
        # to Action.
        self.profile = CC3ProfileFactory.create()

        # Saving the profile activates the cyclos account creation signal.
        # This fails due to difficulty of having a cyclos instance as part of
        # the test setup (ie groups, groupsets etc).
        # self.profile.save()
        self.action_payment_account = CC3ProfileFactory.create()
        # self.action_payment_account.save()
        self.amount_1 = 123
        self.rule_1 = RuleFactory.create(
            action_class=u"",  # cc3.rules.actions.PayCC3Profile",
            parameter_names=u"",  # amount,sender_id",
            parameter_values="",  # ,{0},{1}".format(self.amount_1,
                                  # self.action_payment_account.user.id),
            process_model=ContentType.objects.get_for_model(User),
            instance_identifier='id',
            # exit_on_match           = models.BooleanField(default=False)
            # sequence                = models.IntegerField()
        )

        self.condition_1 = ConditionFactory.create(
            rule=self.rule_1,
            evaluates_field='id',
            evaluate_operator='>=',
            evaluate_expression='1',
            # AND or OR (see Rule)
            # join_condition=JOIN_CONDITIONS[0]
            # = models.CharField(max_length=3,
            # choices=JOIN_CONDITIONS, default='AND')
        )

        self.rule_2 = RuleFactory.create(
            action_class=u"",  # cc3.rules.actions.PayCC3Profile",
            parameter_names=u"",  # amount,sender_id",
            parameter_values="",  # 123",
            process_model=ContentType.objects.get_for_model(User),
            instance_identifier='id',
            # exit_on_match           = models.BooleanField(default=False)
            # sequence                = models.IntegerField()
        )

        self.condition_2 = ConditionFactory.create(
            rule=self.rule_2,
            evaluates_field='date_joined',
            evaluate_operator='<=',
            # datetime.datetime.now() - naive datetime
            # doesn't work with TZ_ True in settings
            evaluate_expression='timezone.now()'
        )

        self.rule_3 = RuleFactory.create(
            action_class=u"",  # cc3.rules.actions.PayCC3Profile",
            parameter_names=u"",  # amount",
            parameter_values="",  # 123",
            process_model=ContentType.objects.get_for_model(User),
            instance_identifier='id',
            # exit_on_match           = models.BooleanField(default=False)
            # sequence                = models.IntegerField()
        )

        self.condition_3 = ConditionFactory.create(
            rule=self.rule_3,
            evaluates_field='date_joined',
            field_expression="dateparse.parse_datetime('{0}').month",
            evaluate_operator='<=',
            # datetime.datetime.now() - naive datetime doesn't work with
            # TZ_ True in settings.
            evaluate_expression='timezone.now().month'
        )

        self.rule_4 = RuleFactory.create(
            action_class=u"",  # cc3.rules.actions.PayCC3Profile",
            parameter_names=u"",  # amount",
            parameter_values="",  # 123",
            process_model=ContentType.objects.get_for_model(User),
            instance_identifier='id',
            # exit_on_match           = models.BooleanField(default=False)
            # sequence                = models.IntegerField()
        )

        self.condition_4 = ConditionFactory.create(
            rule=self.rule_4,
            evaluates_field='date_joined',
            evaluate_operator='is',
            evaluate_expression='None'
        )

    def test_basic_rule(self):
        """
        Test a rule which should always be true, a newly created user.id > 1
        """

        rule_result = self.rule_1.run_evaluate(self.profile.user)
        # returns an id if True or None if False
        self.assertIsNotNone(rule_result)

    def test_date_comparison(self):
        """
        Test a rule which should always be true, a newly created
        user.date_joined < timezone.now()
        """
        rule_result = self.rule_2.run_evaluate(self.profile.user)
        self.assertIsNotNone(rule_result)

    def test_month_comparison(self):
        """
        Test a rule which should always be true, a newly created
        user.date_joined < timezone.now()
        """
        rule_result = self.rule_3.run_evaluate(self.profile.user)
        self.assertIsNotNone(rule_result)

        # TODO test multiple rule exit_on_match and exit_on_fail
        # TODO test field expression

    def test_month_none(self):
        """
        Test a rules which compares a date time field to None
        """
        rule_result = self.rule_4.run_evaluate(self.profile.user)
        self.assertIsNot(rule_result, True)
