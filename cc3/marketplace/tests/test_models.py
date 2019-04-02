from django.core.urlresolvers import reverse
from django.test import TestCase

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.tests.test_factories import (
    CC3CommunityFactory, CC3ProfileFactory, CyclosAccountFactory,
    CyclosGroupFactory, CyclosGroupSetFactory, AuthUserProfileFactory)
from cc3.marketplace.tests.test_factories import AdFactory
from cc3.cyclos.models.account import CC3Profile
from django.conf import settings

class AdTestCase(TestCase):
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.group_2 = CyclosGroupFactory.create()
        self.group_3 = CyclosGroupFactory.create()
        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, self.group_2, self.group_3])

        self.community = CC3CommunityFactory.create(groupsets=[self.groupset])

        self.profile = CC3ProfileFactory.create(community=self.community,
                                                cyclos_group=CyclosGroupFactory(
                                                    name=settings.CYCLOS_CUSTOMER_MEMBER_GROUP))

        self.member_profile = AuthUserProfileFactory.create(
            groupset=self.groupset,
            community=self.community,
            business_name='MaykinMedia',
            web_payments_enabled=True)

        self.member_empty_profile = CC3ProfileFactory.create()

        # Create a Cyclos account for the 'member_profile'.
        self.cyclos_account = CyclosAccountFactory.create(
            cc3_profile=self.profile)

    def test_create_ad_makes_profile_visible(self):
        """
        Test that creating an ad results in the user's profile becoming visible.
        """
        self.assertFalse(self.profile.is_visible)
        ad = AdFactory.create(created_by=self.profile)
        prof = CC3Profile.objects.get(id=self.profile.id)
        self.assertTrue(prof.is_visible)
