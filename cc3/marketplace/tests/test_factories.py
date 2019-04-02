import logging

from django.conf import settings

import factory

from cc3.cyclos.tests.test_factories import CC3ProfileFactory

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class AdTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'marketplace.AdType'

    code = factory.Sequence(lambda n: str(n)[:4])
    title = factory.Sequence(lambda n: 'AdType_{0}'.format(n))


class AdPricingOptionFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'marketplace.AdPricingOption'

    title = factory.Sequence(lambda n: 'AdPricingOption_{0}'.format(n))


class AdPricingOptionTranslationFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'marketplace.AdPricingOptionTranslation'

    title = factory.Sequence(lambda n: 'AdPricingOptionTrans_{0}'.format(n))
    language = settings.LANGUAGE_CODE
    ad_pricing_option = factory.SubFactory(AdPricingOptionFactory)


class AdFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'marketplace.Ad'

    title = factory.Sequence(lambda n: 'Ad_{0}'.format(n))
    adtype = factory.SubFactory(AdTypeFactory)
    description = '{0} description'.format(title)
    price_option = factory.SubFactory(AdPricingOptionFactory)
    created_by = factory.SubFactory(CC3ProfileFactory)

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of AdCategories were passed in, use them.
            for category in extracted:
                self.category.add(category)
