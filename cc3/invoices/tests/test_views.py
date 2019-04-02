import logging

from django.test import TestCase
from django.core.urlresolvers import reverse

from cc3.cyclos.tests.test_factories import (
    UserFactory, CyclosGroupFactory, CyclosGroupSetFactory,
    CC3CommunityFactory, AuthUserProfileFactory)

from .test_factories import InvoiceFactory

LOG = logging.getLogger(__name__)


class InvoiceTestCase(TestCase):
    """
    Test that secured views need a user
    """
    def test_non_auth(self):
        """
        check non-authenticated users cannot access invoice views
        """
        reversed_url = reverse('invoice_list')
        response = self.client.get(reversed_url, follow=True)
        self.assertRedirects(response, '%s?next=%s' % (
            reverse('auth_login'),
            reversed_url
        ))

        reversed_url = reverse('invoice_download_pdf', args=[1, ])
        response = self.client.get(reversed_url, follow=True)
        self.assertRedirects(response, '%s?next=%s' % (
            reverse('auth_login'),
            reversed_url
        ))

        reversed_url = reverse('invoice_download_excel', args=[1, ])
        response = self.client.get(reversed_url, follow=True)
        self.assertRedirects(response, '%s?next=%s' % (
            reverse('auth_login'),
            reversed_url
        ))

    def test_auth(self):
        """
        check authenticated users can access invoice views
        """
        admin_user_1 = UserFactory.create(
            is_staff=True, is_active=True, is_superuser=True)
        cyclos_group_1 = CyclosGroupFactory.create(
            initial=True, invoice_user=admin_user_1)
        cyclos_groupset_1 = CyclosGroupSetFactory.create(
            groups=[cyclos_group_1])
        community_1 = CC3CommunityFactory.create(groupsets=[cyclos_groupset_1])
        profile = AuthUserProfileFactory.create(
             web_payments_enabled=True, community=community_1)
        profile2 = AuthUserProfileFactory.create(
             web_payments_enabled=True, community=community_1)
        self.client.login(
            username=profile.user.username,
            password='testing',
        )

        invoice = InvoiceFactory.create(
            from_user=profile.user,
            to_user=profile2.user
        )
        response = self.client.get(
            reverse('invoice_list'), follow=True)
        self.assertEqual(response.status_code, 200)

        # excel invoice download NotImplementedError
#        response = self.client.get(
#            reverse('invoice_download_excel', args=[invoice.pk, ]),
#            follow=True)
#        self.assertRaises(response, NotImplementedError)

        response = self.client.get(
            reverse('invoice_download_pdf', args=[invoice.pk, ]),
            follow=True)
        self.assertEqual(response.status_code, 200)
