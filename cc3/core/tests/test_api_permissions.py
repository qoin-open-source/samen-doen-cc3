from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.test.client import RequestFactory

from cc3.cyclos.tests.test_factories import (
    CC3ProfileFactory, CommunityAdminFactory)
from cc3.marketplace.tests.test_factories import AdFactory

from ..api.permissions import IsCommunityAdmin, IsAdManager


class IsCommunityAdminTestCase(TestCase):
    """
    Test case for ``IsCommunityAdmin`` API permissions class.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.permission_class = IsCommunityAdmin()

        self.admin_profile = CC3ProfileFactory.create()
        self.member_profile = CC3ProfileFactory.create()

        CommunityAdminFactory.create(
            user=self.admin_profile.user,
            community=self.admin_profile.community
        )

    def test_is_community_admin_login_required(self):
        """
        Tests access denied for non-logged users.
        """
        request = self.factory
        request.user = AnonymousUser()

        self.assertFalse(self.permission_class.has_permission(request, None))

    def test_is_community_admin_is_admin_required(self):
        """
        Tests access denied for non community admin users.
        """
        request = self.factory
        request.user = self.member_profile.user

        self.assertFalse(self.permission_class.has_permission(request, None))

    def test_is_community_admin_access_granted(self):
        """
        Tests access is granted for community admin users.
        """
        request = self.factory
        request.user = self.admin_profile.user

        self.assertTrue(self.permission_class.has_permission(request, None))


class IsAdManagerTestCase(TestCase):
    """
    Test case for ``IsAdManager`` API permissions class.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.permission_class = IsAdManager()

        self.owner_profile = CC3ProfileFactory.create()
        self.member_profile = CC3ProfileFactory.create()

        self.ad = AdFactory.create(created_by=self.owner_profile)

    def test_is_ad_manager_login_required(self):
        """
        Tests access denied for non-logged users.
        """
        request = self.factory
        request.user = AnonymousUser()

        self.assertFalse(self.permission_class.has_permission(request, None))

    def test_is_ad_manager_can_edit_required(self):
        """
        Tests ``can_edit`` condition must be accomplished to access the object.
        """
        request = self.factory
        request.user = self.member_profile.user
        request.method = 'POST'

        self.assertFalse(self.permission_class.has_object_permission(
            request, None, self.ad))

    def test_is_ad_manager_access_granted(self):
        """
        Tests access granted for the owner of the Ad related to the image.
        """
        request = self.factory
        request.user = self.owner_profile.user
        request.method = 'POST'

        self.assertTrue(self.permission_class.has_object_permission(
            request, None, self.ad))
