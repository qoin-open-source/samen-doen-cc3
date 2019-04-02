import logging

import factory
import factory.fuzzy

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class RuleFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'rules.Rule'

    name = factory.Sequence(lambda n: 'rule_{0}'.format(n))
    sequence = factory.Sequence(lambda n: n)


class ConditionFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'rules.Condition'

    rule = factory.SubFactory(RuleFactory)
