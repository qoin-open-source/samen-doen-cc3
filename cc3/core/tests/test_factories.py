import logging

from django.conf import settings

import factory

from cc3.cyclos.tests.test_factories import UserFactory

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class CategoryFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'core.Category'

    title = factory.Sequence(lambda n: 'Category_{0}'.format(n))
    description = '{0} description'.format(title)


class CategoryTranslationFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'core.CategoryTranslation'

    title = factory.Sequence(lambda n: 'CategoryTranslation_{0}'.format(n))
    description = '{0} description'.format(title)
    language = settings.LANGUAGE_CODE
    category = factory.SubFactory(CategoryFactory)


class TransactionFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'core.Transaction'

    amount = factory.Sequence(lambda n: n * 12.5)
    sender = factory.SubFactory(UserFactory)
    receiver = factory.SubFactory(UserFactory)
    transfer_id = factory.Sequence(lambda n: n)
