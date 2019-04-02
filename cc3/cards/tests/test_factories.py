import logging

import factory
import factory.fuzzy


from cc3.cyclos.tests.test_factories import UserFactory

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class CardNumberFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cards.CardNumber'

    uid_number = factory.Sequence(lambda n: '{num:010d}'.format(num=n))
    number = factory.Sequence(lambda n: '{num:05d}'.format(num=n))


class CardTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cards.CardType'


class CardFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cards.Card'

    number = factory.SubFactory(CardNumberFactory)
    owner = factory.SubFactory(UserFactory)
    card_type = factory.SubFactory(CardTypeFactory)


class TerminalFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cards.Terminal'

    name = factory.Sequence(lambda n: 'Terminal_{num:010d}'.format(num=n))
    business = factory.SubFactory(UserFactory)


class OperatorFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cards.Operator'

    business = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: 'Operator_{num:010d}'.format(num=n))
    pin = factory.Sequence(lambda n: '{num:04d}'.format(num=n))
