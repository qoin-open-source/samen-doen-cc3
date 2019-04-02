from django.conf import settings
from django.test import TestCase
from django.utils.translation import get_language, activate

from cc3.core.models import Category
from cc3.core.tests.test_factories import (
    CategoryTranslationFactory, CategoryFactory)
from cc3.marketplace.tests.test_factories import (AdPricingOptionFactory,
    AdPricingOptionTranslationFactory)


class CategoryTranslationTestCase(TestCase):
    """ Test if the correct translation is used for an Category """
    def setUp(self):
        self.category = CategoryFactory.create()
        self.trans_nl = CategoryTranslationFactory.create(
            category=self.category, language='nl', title='dutch',
            description='dutch_desc')
        self.trans_en = CategoryTranslationFactory.create(
            category=self.category, language='en', title='english',
            description='english_desc')

    def tearDown(self):
        """
        Restore the project language to project language code
        """
        activate(settings.LANGUAGE_CODE)

    def test_nl(self):
        cat = Category.objects.get(title=self.category.title)
        activate('nl')
        language = get_language()
        self.assertEqual(language, 'nl')

        self.assertEqual(cat.get_title(), 'dutch')
        self.assertEqual(cat.get_description(), 'dutch_desc')

    def test_en(self):
        cat = Category.objects.get(title=self.category.title)
        activate('en')
        language = get_language()
        self.assertEqual(language, 'en')

        self.assertEqual(cat.get_title(), 'english')
        self.assertEqual(cat.get_description(), 'english_desc')

    def test_sub_lang(self):
        """ check that en-gb still brings back en """
        cat = Category.objects.get(title=self.category.title)
        activate('en-gb')
        language = get_language()
        self.assertEqual(language, 'en-gb')

        self.assertEqual(cat.get_title(), 'english')
        self.assertEqual(cat.get_description(), 'english_desc')

    def test_fallback(self):
        """ check that untranslated languages return the default """
        cat = Category.objects.get(title=self.category.title)
        activate('fr')
        language = get_language()
        self.assertEqual(language, 'fr')

        self.assertEqual(cat.get_title(), self.category.title)
        self.assertEqual(cat.get_description(), self.category.description)


class AdPricingOptionTranslationTestCase(TestCase):
    """ Test if the correct translation is used for an AdPricingOption """

    def setUp(self):
        self.price_option = AdPricingOptionFactory.create()
        self.trans_nl = AdPricingOptionTranslationFactory.create(
            ad_pricing_option=self.price_option, language='nl', title='dutch')
        self.trans_nl = AdPricingOptionTranslationFactory.create(
            ad_pricing_option=self.price_option, language='en',
            title='english')

    def tearDown(self):
        """
        Restore the project language to project language code
        """
        activate(settings.LANGUAGE_CODE)

    def test_nl(self):
        activate('nl')
        self.assertEqual(self.price_option.get_title(), 'dutch')

    def test_en(self):
        activate('en')
        self.assertEqual(self.price_option.get_title(), 'english')

    def test_sub_lang(self):
        """ check that en-gb still brings back en """
        activate('en-gb')
        self.assertEqual(self.price_option.get_title(), 'english')

    def test_fallback(self):
        """ check that untranslated languages return the default """
        activate('fr')
        self.assertEqual(
            self.price_option.get_title(), self.price_option.title)


