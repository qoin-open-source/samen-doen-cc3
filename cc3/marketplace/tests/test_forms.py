from django import forms
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.translation import ugettext as _

from cc3.core.tests.test_factories import CategoryFactory
from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.tests.test_factories import CC3ProfileFactory, UserFactory
from cc3.marketplace.tests.test_factories import AdFactory, AdTypeFactory

from ..forms import AdForm, MarketplacePayForm


class AdFormTestCase(TestCase):
    def setUp(self):
        self.category = CategoryFactory.create()
        self.ad_type = AdTypeFactory.create()

        self.form = AdForm()
        self.test_data = {
            'title': 'Dummy Ad',
            'category': self.category.pk,
            'adtype': self.ad_type.pk,
            'description': 'A dummy Ad for unit testing.',
            'price': 10.5,
            'keywords': 'unittest, python, ci'
        }

    @override_settings(PRICING_SUPPORT=True, PRICING_OPTION_SUPPORT=False)
    def test_clean_price_with_pricing_support(self):
        """
        Tests the ``clean_price`` method when the pricing support is enabled
        and pricing option support is not enabled in the current Django project
        """
        self.test_data['price'] = ''
        self.form.cleaned_data = self.test_data

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'Please, enter a price'),
            self.form.clean_price
        )


    @override_settings(PRICING_SUPPORT=False)
    def test_clean_price_without_pricing_support(self):
        """
        Tests the ``clean_price`` method when the pricing support is disabled
        in the current Django project.
        """
        self.test_data['price'] = ''
        self.form.cleaned_data = self.test_data

        self.assertEqual(self.form.clean_price(), '')


class MarketPlacePayFormTestCase(TestCase):
    """
    Test case for ``MarketplacePayForm``.
    """
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.ad = AdFactory.create()
        self.user = UserFactory.create(
            first_name='Vanessa',
            last_name='Gaultier',
            username='vanessa',
            email='vanessa@maykinmedia.nl'
        )
        self.profile = CC3ProfileFactory.create(user=self.user)

        self.form = MarketplacePayForm(user=self.profile.user)
        self.test_data = {
            'amount': 10.0,
            'contact_name': 'Vanessa Gaultier',
            'description': 'Testing payment',
            'ad': self.ad.pk
        }

    def test_clean_amount_insufficient_balance(self):
        """
        Tests the ``clean_amount`` method when the user who is making the
        payment doesn't have enough credit to pay.
        """
        # This test returns a user who have a credit of 100.00, so we will try
        # here to pass that.
        self.test_data['amount'] = 200.0
        self.form.cleaned_data = self.test_data

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'You do not have sufficient credit to complete the payment'),
            self.form.clean_amount
        )

    def test_clean_amount(self):
        """
        Tests the ``clean_amount`` method when the user is making a payment and
        there is enough credit to do it.
        """
        self.form.cleaned_data = self.test_data

        self.assertEqual(self.form.clean_amount(), self.test_data['amount'])
