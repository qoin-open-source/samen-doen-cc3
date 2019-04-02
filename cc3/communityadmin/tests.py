import unittest

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory

from cc3.communityadmin.views import ContentListView, MemberListView
from cc3.core.tests.test_factories import CategoryFactory
from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.tests.test_factories import (
    CC3ProfileFactory, CommunityAdminFactory, CommunityMessageFactory,
    CC3CommunityFactory, CMSPlaceholderFactory, CMSPageFactory,
    CommunityPluginModelFactory, CyclosGroupFactory, CyclosGroupSetFactory,
    CyclosAccountFactory)
from cc3.cyclos.backends import set_backend
from cc3.marketplace.tests.test_factories import AdFactory


class ContentListViewTestCase(TestCase):
    """
    Test case for the ``ContentListView`` class-based view.
    """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        # Django CMS Page.
        self.placeholder = CMSPlaceholderFactory.create()
        self.page = CMSPageFactory.create(placeholders=(self.placeholder,))

        self.url = reverse('communityadmin_ns:contentlist')

        self.profile = CC3ProfileFactory.create()
        self.anonymous_profile = CC3ProfileFactory.create()

        CommunityAdminFactory.create(
            user=self.profile.user,
            community=self.profile.community
        )

        # Create a separated Community.
        self.community = CC3CommunityFactory.create()

        # Create some Community messages. `CommunityMessages` belong to a
        # Django CMS `CommunityPlugin`.
        self.plugin = CommunityPluginModelFactory.create(
            placeholder=self.placeholder)

        self.message_1 = CommunityMessageFactory.create(
            plugin=self.plugin,
            community=self.community,
            plugin__placeholder__page__publisher_is_draft=True)
        self.message_2 = CommunityMessageFactory.create(
            plugin=self.plugin,
            community=self.profile.community,
            plugin__placeholder__page__publisher_is_draft=True)
        self.message_3 = CommunityMessageFactory.create(
            plugin=self.plugin,
            community=self.profile.community,
            plugin__placeholder__page__publisher_is_draft=True)

        self.factory = RequestFactory()

    def test_contentlist_login_required(self):
        """
        Tests that be logged is required to access the ``contentlist`` view.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_contentlist_permission_allowed_community_admin(self):
        """
        Tests permission allowed for community admins to ``contentlist`` view.
        """
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_contentlist_permission_denied_non_community_member_user(self):
        """
        Tests permission denied for those users who are not members of this
        community in ``contentlist`` view.
        """
        self.client.login(
            username=self.anonymous_profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_contentlist_get_queryset(self):
        """
        Tests that the ``get_queryset`` method returns the correct set of
        Community messages.
        """
        request = self.factory.get(self.url)
        request.user = self.profile.user

        view = ContentListView()
        view.request = request

        # Only those messages related to a Django CMS draft `Page` must be
        # shown. We'll set to 'draft' all of them, but only the `message_2`
        # and the `message_3` are related to the current community, so those
        # must be the only to be shown.
        self.message_1.plugin.placeholder.page.publisher_is_draft = True
        self.message_1.plugin.placeholder.page.save()
        self.message_2.plugin.placeholder.page.publisher_is_draft = True
        self.message_2.plugin.placeholder.page.save()
        self.message_3.plugin.placeholder.page.publisher_is_draft = True
        self.message_3.plugin.placeholder.page.save()

        self.assertQuerysetEqual(
            view.get_queryset(),
            [repr(self.message_2), repr(self.message_3)])


class MemberListViewTestCase(TestCase):
    """
    Test case for the ``MemberListView`` class-based view.
    """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.url = reverse('communityadmin_ns:memberlist')

        self.profile = CC3ProfileFactory.create()
        self.anonymous_profile = CC3ProfileFactory.create()

        CommunityAdminFactory.create(
            user=self.profile.user,
            community=self.profile.community
        )

        self.member_1 = CC3ProfileFactory.create(
            community=self.profile.community)
        self.member_2 = CC3ProfileFactory.create()
        self.member_3 = CC3ProfileFactory.create()

        self.factory = RequestFactory()

    def test_memberlist_login_required(self):
        """
        Tests that be logged is required to access the ``memberlist`` view.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_memberlist_permission_allowed_community_admin(self):
        """
        Tests permission allowed for community admins to ``memberlist`` view.
        """
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_memberlist_permission_denied_non_community_member_user(self):
        """
        Tests permission denied for those users who are not members of this
        community in ``memberlist`` view.
        """
        self.client.login(
            username=self.anonymous_profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_memberlist_get_queryset_admin_user(self):
        """
        Tests that the ``get_queryset`` method returns proper members list for
        a community admin user.
        """
        # Create a dummy request made by a community admin.
        request = self.factory.get(self.url)
        request.user = self.profile.user

        # Test the response of the method.
        view = MemberListView()
        view.request = request

        # The returned queryset must contain the `member_1`, since it is the
        # only one who is member of the same community as `profile` user, and
        # the `profile` user itself.
        community = self.profile.community
        members = community.cc3profile_set.order_by('-user__date_joined')
        community_member_objs = view.get_queryset()
        self.assertQuerysetEqual(
            [cm.member() for cm in community_member_objs],
            [repr(member) for member in members],
            ordered=False)


class TransactionListViewTestCase(TestCase):
    """
    Test case for ``TransactionListView`` class-based view.
    """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        self.url = reverse('communityadmin_ns:transactions')

        self.profile = CC3ProfileFactory.create()
        self.anonymous_profile = CC3ProfileFactory.create()

        CommunityAdminFactory.create(
            user=self.profile.user,
            community=self.profile.community
        )

    def test_transactions_login_required(self):
        """
        Tests that be logged is required to access the ``transactions`` view.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    @unittest.skip('Skipping test')
    def test_transactions_permission_allowed_community_admin(self):
        """
        Tests permission allowed for community admins to ``transaction`` view.
        """
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_transactions_permission_denied_non_community_member_user(self):
        """
        Tests permission denied for those users who are not members of this
        community in ``transaction`` view.
        """
        self.client.login(
            username=self.anonymous_profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class MemberWantsOfferViewTestCase(TestCase):
    """
    Test case for ``MemberWantsOfferView`` class-based view.
    """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        group_1 = CyclosGroupFactory.create()
        group_2 = CyclosGroupFactory.create()
        group_3 = CyclosGroupFactory.create()
        self.groupset = CyclosGroupSetFactory.create(
            groups=[group_1, group_2, group_3])

        self.profile = CC3ProfileFactory.create()
        self.member_profile = CC3ProfileFactory.create(groupset=self.groupset)
        self.member_empty_profile = CC3ProfileFactory.create()

        CommunityAdminFactory.create(
            user=self.profile.user,
            community=self.profile.community
        )

    def test_memberwants_offers_login_required(self):
        """
        Tests that be logged is required to access the ``memberwantsoffers``
        view.
        """
        url = reverse(
            'communityadmin_ns:memberwantsoffers',
            kwargs={'username': self.member_profile.user.username})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

    def test_memberwants_offers_user_without_groupset(self):
        """
        Tests permission denied when trying to access the view for a user who
        does not have yet a groupset defined.
        """
        url = reverse(
            'communityadmin_ns:memberwantsoffers',
            kwargs={'username': self.member_empty_profile.user.username})
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_memberwants_offers_permission_allowed_community_admin(self):
        """
        Tests permission allowed for community admins to ``memberwantsoffers``
        view.
        """
        url = reverse(
            'communityadmin_ns:memberwantsoffers',
            kwargs={'username': self.member_profile.user.username})
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_memberwants_offers_permission_denied_non_community_member_user(self):
        """
        Tests permission denied for those users who are not members of this
        community in ``memberwantsoffers`` view.
        """
        url = reverse(
            'communityadmin_ns:memberwantsoffers',
            kwargs={'username': self.member_profile.user.username})
        self.client.login(
            username=self.member_profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_memberwants_offers_404_non_existent_user(self):
        """
        Tests that the view returns a 404 error when a non existent user is
        requested.
        """
        url = reverse(
            'communityadmin_ns:memberwantsoffers',
            kwargs={'username': 'non_existent_user'})
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class ChangePasswordViewTestCase(TestCase):
    """
    Test case for the ``ChangePasswordView`` class-based view.
    """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        group_1 = CyclosGroupFactory.create()
        group_2 = CyclosGroupFactory.create()
        group_3 = CyclosGroupFactory.create()
        self.groupset = CyclosGroupSetFactory.create(
            groups=[group_1, group_2, group_3])

        self.profile = CC3ProfileFactory.create()
        self.member_profile = CC3ProfileFactory.create(groupset=self.groupset)
        self.member_empty_profile = CC3ProfileFactory.create()

        CommunityAdminFactory.create(
            user=self.profile.user,
            community=self.profile.community
        )

    def test_changepassword_login_required(self):
        """
        Tests that be logged is required to access the ``changepassword``
        view.
        """
        url = reverse(
            'communityadmin_ns:changepassword',
            kwargs={'username': self.member_profile.user.username})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

    def test_changepassword_permission_allowed_community_admin(self):
        """
        Tests permission allowed for community admins to ``changepassword``
        view.
        """
        url = reverse(
            'communityadmin_ns:changepassword',
            kwargs={'username': self.member_profile.user.username})
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_changepassword_permission_denied_non_community_member_user(self):
        """
        Tests permission denied for those users who are not members of this
        community in ``changepassword`` view.
        """
        url = reverse(
            'communityadmin_ns:changepassword',
            kwargs={'username': self.member_profile.user.username})
        self.client.login(
            username=self.member_profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_changepassword_404_non_existent_user(self):
        """
        Tests that the view returns a 404 error when a non existent user is
        requested.
        """
        url = reverse(
            'communityadmin_ns:changepassword',
            kwargs={'username': 'non_existent_user'})
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class ChangeGroupViewTestCase(TestCase):
    """
    Test case for the ``ChangeGroupView`` class-based view.
    """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.group_2 = CyclosGroupFactory.create()
        self.group_3 = CyclosGroupFactory.create()
        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, self.group_2, self.group_3])

        self.community = CC3CommunityFactory.create(groupsets=[self.groupset])

        self.profile = CC3ProfileFactory.create(community=self.community)
        self.member_profile = CC3ProfileFactory.create(
            groupset=self.groupset, community=self.community)
        self.member_empty_profile = CC3ProfileFactory.create()

        CommunityAdminFactory.create(
            user=self.profile.user,
            community=self.profile.community
        )

        # Create a Cyclos account for the 'member_profile'.
        self.cyclos_account = CyclosAccountFactory.create(
            cc3_profile=self.member_profile)

    def test_changegroup_login_required(self):
        """
        Tests that be logged is required to access the ``changegroup``
        view.
        """
        url = reverse(
            'communityadmin_ns:changegroup',
            kwargs={'username': self.member_profile.user.username})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

    def test_changegroup_permission_allowed_community_admin(self):
        """
        Tests permission allowed for community admins to ``changegroup``
        view.
        """
        url = reverse(
            'communityadmin_ns:changegroup',
            kwargs={'username': self.member_profile.user.username})
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_changegroup_permission_denied_non_community_member_user(self):
        """
        Tests permission denied for those users who are not members of this
        community in ``changegroup`` view.
        """
        url = reverse(
            'communityadmin_ns:changegroup',
            kwargs={'username': self.member_profile.user.username})
        self.client.login(
            username=self.member_profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_changegroup_404_non_existent_user(self):
        """
        Tests that the view returns a 404 error when a non existent user is
        requested.
        """
        url = reverse(
            'communityadmin_ns:changegroup',
            kwargs={'username': 'non_existent_user'})
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_change_group_successful(self):
        """
        Tests a successful POST over ``changegroup`` view. This should change
        the group for the corresponding profile and redirect to the
        ``memberlist`` view.
        """
        post_data = {
            'groups': self.group_2.pk,
            'comments': 'Testing group change.'
        }

        url = reverse(
            'communityadmin_ns:changegroup',
            kwargs={'username': self.member_profile.user.username})

        # Only the community administrators should be able to perform this.
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.post(url, post_data)

        # The status code will be '302' in a successful POST, because of the
        # response redirection.
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('communityadmin_ns:memberlist'))


class CommunityAdUpdateViewTestCase(TestCase):
    """
    Test case for ``CommunityAdUpdate`` class-based view.
    """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.group_2 = CyclosGroupFactory.create()
        self.group_3 = CyclosGroupFactory.create()
        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, self.group_2, self.group_3])

        self.community = CC3CommunityFactory.create(groupsets=[self.groupset])

        self.profile = CC3ProfileFactory.create(community=self.community)
        self.member_profile = CC3ProfileFactory.create(
            groupset=self.groupset, community=self.community)
        self.member_empty_profile = CC3ProfileFactory.create()

        CommunityAdminFactory.create(
            user=self.profile.user,
            community=self.profile.community
        )

        # Create a Cyclos account for the 'member_profile'.
        self.cyclos_account = CyclosAccountFactory.create(
            cc3_profile=self.member_profile)

        self.ad = AdFactory.create(created_by=self.member_profile)

        self.url = reverse(
            'communityadmin_ns:edit_ad', kwargs={'pk': self.ad.pk})

    def test_comm_edit_ad_login_required(self):
        """
        Tests that be logged is required to access the ``edit_ad``
        view.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_comm_edit_ad_permission_allowed_community_admin(self):
        """
        Tests permission allowed for community admins to ``edit_ad``
        view.
        """
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_comm_edit_ad_permission_denied_non_community_member_user(self):
        """
        Tests permission denied for those users who are not members of this
        community in ``edit_ad`` view.
        """
        self.client.login(
            username=self.member_profile.user.username, password='testing')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_comm_edit_ad_post_success(self):
        """
        Tests a successful POST operation over ``edit_ad`` view. This should
        change the current Ad and return 'OK' (200) so the javascript can
        redirect to community admin ``wantsoffers`` view.
        """
        new_category = CategoryFactory.create()

        post_data = {
            'title': 'New title',
            'category': new_category.pk,
            'description': 'Updated description',
            'price': 10.5,
            'adtype': self.ad.adtype.pk
        }

        # Only the community administrators should be able to perform this.
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.post(self.url, post_data)

#        self.assertEqual(response.status_code, 302)
#        self.assertRedirects(response, reverse('communityadmin_ns:wantsoffers'))

        # view actually returns a 200 and the redirect happens via javascript
        # the form is submitted via Ajax to maintain file upload choices if there are
        # errors.
        # TODO: Check that the edit ad submit degrades when no javascript is present
        self.assertEqual(response.status_code, 200)
        #self.assertRedirects(response, reverse('communityadmin_ns:wantsoffers'))
