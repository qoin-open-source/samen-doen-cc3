from decimal import Decimal

import factory

from cc3.cyclos.tests.test_factories import UserFactory, CC3CommunityFactory


class BusinessCauseSettingsFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'rewards.BusinessCauseSettings'

    user = factory.SubFactory(UserFactory)
    transaction_percentage = Decimal('10.0')
    reward_percentage = True


class UserCauseFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'rewards.UserCause'

    consumer = factory.SubFactory(UserFactory)
    cause = factory.SubFactory(UserFactory)


class DefaultGoodCauseUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'rewards.DefaultGoodCause'

    community = factory.SubFactory(CC3CommunityFactory)
    cause = factory.SubFactory(UserFactory)