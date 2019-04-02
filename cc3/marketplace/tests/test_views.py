from django.core.urlresolvers import reverse
from django.test import TestCase

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.tests.test_factories import (
    CC3CommunityFactory, CC3ProfileFactory, CyclosAccountFactory,
    CyclosGroupFactory, CyclosGroupSetFactory, AuthUserProfileFactory)
from cc3.marketplace.tests.test_factories import AdFactory, AdTypeFactory

class MarketplaceAdCreateViewTestCase(TestCase):
    """
       Test case for ``MarketplaceAdUpdateView`` class-based view.
       """
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.group_2 = CyclosGroupFactory.create()
        self.group_3 = CyclosGroupFactory.create()
        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, self.group_2, self.group_3])

        self.community = CC3CommunityFactory.create(groupsets=[self.groupset])

        self.profile = CC3ProfileFactory.create(community=self.community)
        self.member_profile = AuthUserProfileFactory.create(
            groupset=self.groupset,
            community=self.community,
            business_name='MaykinMedia',
            web_payments_enabled=True)

        self.member_empty_profile = CC3ProfileFactory.create()

        # Create a Cyclos account for the 'member_profile'.
        self.cyclos_account = CyclosAccountFactory.create(
            cc3_profile=self.profile)

        self.url = reverse('accounts_place_ad')

    def test_marketplace_create_ad_login_required(self):
        """
            Tests that be logged is required to access the ``accounts_place_ad``
            view.
            """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class MarketplaceAdUpdateViewTestCase(TestCase):
    """
    Test case for ``MarketplaceAdUpdateView`` class-based view.
    """
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.group_2 = CyclosGroupFactory.create()
        self.group_3 = CyclosGroupFactory.create()
        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, self.group_2, self.group_3])

        self.community = CC3CommunityFactory.create(groupsets=[self.groupset])

        self.profile = CC3ProfileFactory.create(community=self.community)
        self.member_profile = AuthUserProfileFactory.create(
            groupset=self.groupset,
            community=self.community,
            business_name='MaykinMedia',
            web_payments_enabled=True)

        self.member_empty_profile = CC3ProfileFactory.create()

        # Create a Cyclos account for the 'member_profile'.
        self.cyclos_account = CyclosAccountFactory.create(
            cc3_profile=self.profile)

        self.ad = AdFactory.create(created_by=self.profile)

        self.url = reverse(
            'accounts_edit_ad', kwargs={'pk': self.ad.pk})

    def test_marketplace_edit_ad_login_required(self):
        """
        Tests that be logged is required to access the ``accounts_edit_ad``
        view.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_marketplace_edit_ad_permission_denied_no_owner(self):
        """
        Tests permission denied for users who are not owners of this Ad.
        """
        self.client.login(
            username=self.member_profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
