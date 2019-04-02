import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

from cc3.cyclos.tests.test_factories import UserFactory, CommunityAdminFactory
from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.tests.test_factories import (
    CC3CommunityFactory, CC3ProfileFactory,
    CyclosGroupFactory, CyclosGroupSetFactory)
from django.utils.translation import activate

from .test_factories import InvoiceFactory


LOG = logging.getLogger(__name__)


class DownloadInvoicePDFTestCase(TestCase):
    """ Test case to ensure downloading invoices can only be done by the
    appropriate users """

    def setUp(self):
        activate(settings.LANGUAGE_CODE)
        set_backend(DummyCyclosBackend())

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.group_2 = CyclosGroupFactory.create()
        self.group_3 = CyclosGroupFactory.create()

        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, self.group_2, self.group_3])

        self.community = CC3CommunityFactory.create(groupsets=[self.groupset])

        self.from_profile = CC3ProfileFactory.create(community=self.community)
        self.to_profile = CC3ProfileFactory.create(
            groupset=self.groupset,
            community=self.community,
            business_name='MaykinMedia')

        self.invoice = InvoiceFactory.create(from_user=self.from_profile.user,
                                             to_user=self.to_profile.user)
        self.user_1 = UserFactory.create()
        self.staff_user = UserFactory.create(is_staff=True)

        self.community_admin_profile = CC3ProfileFactory.create(
            community=self.community)
        self.community_admin = CommunityAdminFactory.create(
            user=self.community_admin_profile.user,
            community=self.community
        )
        self.url = reverse('invoice_download_pdf',
                           args=[self.invoice.id])

    def test_from_user_download_invoice(self):
        self.client.login(
            username=self.invoice.from_user.username, password='testing')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_to_user_download_invoice(self):
        self.client.login(
            username=self.invoice.to_user.username, password='testing')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_other_user_download_invoice(self):
        self.client.login(
            username=self.user_1.username, password='testing')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_staff_user_download_invoice(self):
        self.client.login(
            username=self.staff_user.username, password='testing')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_community_admin_download_invoice(self):
        self.client.login(
            username=self.community_admin_profile.user.username,
            password='testing')
        response = self.client.get(self.url)
        LOG.info(self.url)
        LOG.info(str(response.status_code))
        self.assertEqual(response.status_code, 200)
