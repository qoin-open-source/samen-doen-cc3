from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from .templatetags.google_analytics import google_analytics


class GoogleAnalyticsTestCase(TestCase):
    """
    Test case for the ``google_analytics`` template tag.
    """
    def setUp(self):
        try:
            del settings.GOOGLE_ANALYTICS_ID
        except AttributeError:
            pass

        try:
            del settings.GOOGLE_ANALYTICS_DOMAIN
        except AttributeError:
            pass

    @override_settings(GOOGLE_ANALYTICS_DOMAIN='community-currency.org')
    def test_no_id(self):
        """
        Tests that template tag returns an empty string when the setting
        ``GOOGLE_ANALYTICS_ID`` is not present.
        """
        self.assertEqual(
            google_analytics(),
            {
                'GOOGLE_ANALYTICS_ID': '',
                'GOOGLE_ANALYTICS_DOMAIN': 'community-currency.org'
            }
        )

    @override_settings(GOOGLE_ANALYTICS_ID='UA-12345678-1')
    def test_no_id(self):
        """
        Tests that template tag returns an empty string when the setting
        ``GOOGLE_ANALYTICS_DOMAIN`` is not present.
        """
        self.assertEqual(
            google_analytics(),
            {
                'GOOGLE_ANALYTICS_ID': 'UA-12345678-1',
                'GOOGLE_ANALYTICS_DOMAIN': ''
            }
        )

    @override_settings(GOOGLE_ANALYTICS_ID='UA-12345678-1')
    @override_settings(GOOGLE_ANALYTICS_DOMAIN='community-currency.org')
    def test_no_id(self):
        """
        Tests that template tag returns an empty string when the settings for
        Google Analytics are present.
        """
        self.assertEqual(
            google_analytics(),
            {
                'GOOGLE_ANALYTICS_ID': 'UA-12345678-1',
                'GOOGLE_ANALYTICS_DOMAIN': 'community-currency.org'
            }
        )
