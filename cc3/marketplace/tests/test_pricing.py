import logging

from django.conf import settings
from django.test import TestCase

from cc3.cyclos.backends import set_backend
from cc3.core.utils.test_backend import DummyCyclosBackend

from cc3.cyclos.tests.test_factories import CC3ProfileFactory
from cc3.marketplace.tests.test_factories import (
    AdPricingOptionFactory, AdFactory)

from ..common import AD_STATUS_ACTIVE, AD_STATUS_DISABLED, AD_STATUS_ONHOLD


LOG = logging.getLogger(__name__)


class AdPricingTestCase(TestCase):
    """ Test if the correct price or price option is shown when viewing an
    Ad """

    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.profile = CC3ProfileFactory.create()
        self.price_option = AdPricingOptionFactory.create(title='TBD')

        self.ad_1 = AdFactory.create(price='10.0', created_by=self.profile,
                                     status=AD_STATUS_ACTIVE)
        self.ad_2 = AdFactory.create(created_by=self.profile,
                                     price_option=self.price_option)

    def test_price_shown(self):
        self.assertEqual(self.ad_1.get_price(), '10.0')
        self.assertEqual(self.ad_2.get_price(), 'TBD')

    def test_view_ad_anonymous(self):
        ad_1_absolute_url = self.ad_1.get_absolute_url()
        response = self.client.get(ad_1_absolute_url)
        self.assertEqual(response.status_code, 200)

    def test_view_ads(self):
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(self.ad_1.get_absolute_url())
        self.assertEqual(response.status_code, 200)

#        try:
#            self.assertContains(response, '10.00</span>')
#        except AssertionError:
#            # Take care of the different forms of specifying decimals,
#            # depending on the country/language.
#            self.assertContains(response, '10,00</span>')
#
        response = self.client.get(self.ad_2.get_absolute_url())
        self.assertEqual(response.status_code, 200)
#        self.assertContains(response, '<span class="a">TBD</span>')


class AdDetailTestCase(TestCase):
    """ Test if the correct price or price option is shown when viewing an
    Ad """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.profile_1 = CC3ProfileFactory.create()
        self.profile_2 = CC3ProfileFactory.create()

        self.price_option = AdPricingOptionFactory.create(title='TBD')
        self.ad_active = AdFactory.create(
            price='10.0', status=AD_STATUS_ACTIVE, created_by=self.profile_1)
        self.ad_disabled = AdFactory.create(
            price='10.0', status=AD_STATUS_DISABLED, created_by=self.profile_1)
        self.ad_onhold = AdFactory.create(
            price='10.0', status=AD_STATUS_ONHOLD, created_by=self.profile_1)

    def test_view_ads_anonymous(self):
        """ Anonymous users may only see active ads """
        response = self.client.get(self.ad_active.get_absolute_url())
        LOG.info('self.ad_active.get_absolute_url() = {0}'.format(self.ad_active.get_absolute_url()))
        LOG.info('response.status_code = {0}'.format(response.status_code))
        self.assertContains(response, self.ad_active.title)
        response = self.client.get(self.ad_disabled.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.ad_onhold.get_absolute_url())
        self.assertEqual(response.status_code, 403)

    def test_view_ads_other_user(self):
        """ Logged-in users may only see the active ads of other users """
        self.client.login(
            username=self.profile_2.user.username, password='testing')
        response = self.client.get(self.ad_active.get_absolute_url())
        self.assertContains(response, self.ad_active.title)
        response = self.client.get(self.ad_disabled.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.ad_onhold.get_absolute_url())
        self.assertEqual(response.status_code, 403)

    def test_view_ads_owner(self):
        """ A user is always allowed to view their own ad """
        self.client.login(
            username=self.profile_1.user.username, password='testing')
        response = self.client.get(self.ad_active.get_absolute_url())
        self.assertContains(response, self.ad_active.title)
        response = self.client.get(self.ad_disabled.get_absolute_url())
        self.assertContains(response, self.ad_disabled.title)
        response = self.client.get(self.ad_onhold.get_absolute_url())
        self.assertContains(response, self.ad_onhold.title)
