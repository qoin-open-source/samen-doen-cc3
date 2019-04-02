# encoding: utf-8
import json
import logging

from datetime import datetime
from decimal import Decimal
from unittest import skipIf

from django.conf import settings
from django.core.urlresolvers import reverse, resolve, NoReverseMatch
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils.translation import ugettext as _, activate

from mock import MagicMock, patch

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.tests.test_factories import (
    UserFactory, CyclosGroupFactory, CyclosGroupSetFactory,
    CC3CommunityFactory, CyclosAccountFactory, AuthUserProfileFactory)
from cc3.cyclos.backends import set_backend
from cc3.cyclos.common import Transaction
from cc3.cyclos.services import (
    AccountNotFoundException, MemberNotFoundException)
from cc3.cyclos.transactions import CyclosBackend
from cc3.marketplace.models import AdPaymentTransaction

from ..forms import (
    TradeQoinPayDirectForm, TradeQoinSplitPayDirectForm,
    TransactionsSearchForm)
from ..views import (
    PayDirectFormView, TransactionsListView, TransactionsSearchListView)

LOG = logging.getLogger(__name__)


class AccountTests(TestCase):

    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        admin_user_1 = UserFactory.create(
            is_staff=True, is_active=True, is_superuser=True)
        cyclos_group_1 = CyclosGroupFactory.create(
            initial=True, invoice_user=admin_user_1)
        cyclos_groupset_1 = CyclosGroupSetFactory.create(
            groups=[cyclos_group_1])
        community_1 = CC3CommunityFactory.create(groupsets=[cyclos_groupset_1])

        admin_user_2 = UserFactory.create(is_superuser=True)
        cyclos_group_2 = CyclosGroupFactory.create(
            initial=True, invoice_user=admin_user_2)
        cyclos_groupset_2 = CyclosGroupSetFactory.create(
            groups=[cyclos_group_2])
        community_2 = CC3CommunityFactory.create(groupsets=[cyclos_groupset_2])

        self.profile = AuthUserProfileFactory.create(
            web_payments_enabled=True, community=community_1)
        self.cyclos_account = CyclosAccountFactory.create(
            cc3_profile=self.profile)
        self.profile_2 = AuthUserProfileFactory.create(
            web_payments_enabled=True)
        self.profile_3 = AuthUserProfileFactory.create(community=community_2)
        self.incomplete_profile = AuthUserProfileFactory.create(
            first_name="Bob",
            last_name="Smith",
            business_name="",
            community=community_2
        )
        self.cyclos_group_for_mock = CyclosGroupFactory.create(
            initial=True, name="Mock Group")

#    def tearDown(self):
#        activate(settings.LANGUAGE_CODE)

    @skipIf(settings.AUTH_PROFILE_MODULE != 'cyclos.CC3Profile',
            u'Skipped as AUTH_PROFILE_MODULE not cyclos.CC3Profile')
    def test_update_profile_view(self):
        # SAMEN DOEN - never returns a 200, always a 404 as no 'profiletype'
        # related model it isn't possible to
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(
            reverse('accounts-update-profile'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/update_my_profile.html')

    def test_close_account_view(self):
        self.client.login(
            username=self.profile.user.username, password='testing')

        response = self.client.get(
            reverse('accounts_close'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/close_account.html')

    @override_settings(GROUPS_ALLOWED_TO_CLOSE_ACCOUNT=['Mock Group', ])
    @patch('cc3.cyclos.models.CC3Profile.get_cyclos_group')
    def test_really_close_account_view(self, mock):
        self.client.login(
            username=self.profile.user.username, password='testing')

        mock.return_value = self.cyclos_group_for_mock

        response = self.client.get(
            reverse('accounts_really_close'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/really_close_account.html')

    @override_settings(GROUPS_ALLOWED_TO_CLOSE_ACCOUNT=['Some Other Group', ])
    @patch('cc3.cyclos.models.CC3Profile.get_cyclos_group')
    def test_really_close_account_view_wrong_group(self, mock):
        self.client.login(
            username=self.profile.user.username, password='testing')

        mock.return_value = self.cyclos_group_for_mock

        response = self.client.get(
            reverse('accounts_really_close'), follow=True)
        self.assertEqual(response.status_code, 403)

    @override_settings(PAYPAL_DOMAIN='paypal.example.com')
    @override_settings(PAYPAL_BUTTON_ID='12345')
    def test_add_funds_view(self):
        self.client.login(
            username=self.profile.user.username, password='testing')

        # TEMPLATE is in cc3/core/templates/marketplace/add_funds.html

        response = self.client.get(
            reverse('add-funds'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/add_funds.html')

    def test_security_view(self):
        self.client.login(
            username=self.profile.user.username, password='testing')

        response = self.client.get(
            reverse('accounts_security'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/accounts_security.html')

    @override_settings(ACCOUNTS_FORCE_COMPLETION=True)
    @skipIf(settings.AUTH_PROFILE_MODULE != 'cyclos.CC3Profile',
            u'Skipped as AUTH_PROFILE_MODULE not cyclos.CC3Profile')
    def test_force_profile_completion(self):
        """ test that enabling ACCOUNTS_FORCE_COMPLETION redirects to
        reverse 'accounts-update-profile'"""

        self.client.login(
            username=self.incomplete_profile.user.username, password='testing'
        )

        response = self.client.get(
            reverse('accounts_pay_direct'), follow=True)
        self.assertEqual(response.status_code, 302)

        self.assertRedirects(
            response, reverse('accounts-update-profile'))


class CreditTests(TestCase):
    """ Test if the credit view works as expected """

    def setUp(self):
        activate('en')
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        admin_user_1 = UserFactory.create(
            is_staff=True, is_active=True, is_superuser=True)
        cyclos_group_1 = CyclosGroupFactory.create(
            initial=True, invoice_user=admin_user_1)
        cyclos_groupset_1 = CyclosGroupSetFactory.create(
            groups=[cyclos_group_1])
        community_1 = CC3CommunityFactory.create(groupsets=[cyclos_groupset_1])

        admin_user_2 = UserFactory.create(is_superuser=True)
        cyclos_group_2 = CyclosGroupFactory.create(
            initial=True, invoice_user=admin_user_2)
        cyclos_groupset_2 = CyclosGroupSetFactory.create(
            groups=[cyclos_group_2])
        community_2 = CC3CommunityFactory.create(groupsets=[cyclos_groupset_2])

        self.profile = AuthUserProfileFactory.create(
            web_payments_enabled=True, community=community_1)
        self.cyclos_account = CyclosAccountFactory.create(
            cc3_profile=self.profile)
        self.profile_2 = AuthUserProfileFactory.create(
            web_payments_enabled=True)
        self.profile_3 = AuthUserProfileFactory.create(community=community_2)

    def tearDown(self):
        activate(settings.LANGUAGE_CODE)

    def test_credit_view(self):
        self.client.login(
            username=self.profile.user.username, password='testing')

        # Verify the credit view works without having added CMS placeholders
        response = self.client.get(
            reverse('accounts-credit'), follow=True)

        # if TRIAL accounts exist, user goes through application process first
        if not getattr(settings, 'CYCLOS_HAS_TRIAL_ACCOUNTS', True):
            self.assertEqual(response.status_code, 200)
            if self.profile.has_full_account():
                self.assertTemplateUsed(response, 'accounts/apply.html')
            else:
                self.assertTemplateUsed(response, 'accounts/credit.html')

    @skipIf(settings.AUTH_PROFILE_MODULE != 'cyclos.CC3Profile',
            u'Skipped as AUTH_PROFILE_MODULE not cyclos.CC3Profile')
    def test_direct_payment_view_login_required(self):
        """
        Tests login required to access 'pay direct' page.
        """
        response = self.client.get(
            reverse('accounts_pay_direct'))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '{0}?next={1}'.format(
                reverse('auth_login'),
                reverse('accounts_pay_direct')))

    @skipIf(settings.AUTH_PROFILE_MODULE != 'cyclos.CC3Profile',
            u'Skipped as AUTH_PROFILE_MODULE not cyclos.CC3Profile')
    def test_direct_payment_view_get_success(self):
        """ Test 'pay direct' page """
        self.client.login(
            username=self.profile.user.username, password='testing')

        response = self.client.get(
            reverse('accounts_pay_direct'), follow=True)

        self.assertContains(response, _('Make A Payment'))
        self.assertContains(response, _('Amount'))
        self.assertNotContains(response, _('Total value of this trade'))
        self.assertEqual(AdPaymentTransaction.objects.count(), 0)

    @skipIf(settings.AUTH_PROFILE_MODULE != 'cyclos.CC3Profile',
            u'Skipped as AUTH_PROFILE_MODULE not cyclos.CC3Profile')
    @patch('cc3.cyclos.backends.user_payment')
    def test_direct_payment_view_post(self, mock):
        """ Verify we can make payments using the DummyCyclosBackend """
        self.client.login(
            username=self.profile.user.username, password='testing')

        # Mock the ``user_payment`` method to avoid hitting Cyclos backend and
        # still have an expected nice response from it.
        mock.return_value = Transaction(
            sender=self.profile.user,
            recipient=self.profile_2.user,
            amount=10,
            created=datetime.now(),
            description='test_payment',
            transfer_id=63
        )

        response = self.client.post(
            reverse('accounts_pay_direct'),
            {
                'amount': '10',
                'contact_name': 'Foo bar (Test business)',
                'profile': self.profile_2.id,
                'description': 'test payment'
            })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse('accounts_home'))
        self.assertEqual(AdPaymentTransaction.objects.count(), 1)

        # Ensure the entries in the payment log are correct
        payment = AdPaymentTransaction.objects.latest('pk')
        self.assertEqual(payment.amount, Decimal('10.0'))
        self.assertEqual(payment.ad, None)
        self.assertEqual(payment.title, 'test payment')
        self.assertEqual(payment.sender, self.profile.user)
        self.assertEqual(payment.receiver, self.profile_2.user)
        self.assertEqual(payment.transfer_id, 63)
        self.assertEqual(payment.split_payment_total_amount, None)

    @skipIf(settings.AUTH_PROFILE_MODULE != 'cyclos.CC3Profile',
            u'Skipped as AUTH_PROFILE_MODULE not cyclos.CC3Profile')
    def test_direct_split_payment_view(self):
        """ Verify we can make split payments using the DummyCyclosBackend """
        # Monkey-patch our backend to return the group with split-payments
        # allowed.
        self.backend.dummy_group_id = 124

        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(
            reverse('accounts_pay_direct'), follow=True)

        self.assertContains(response, _('Make A Payment'))
        self.assertContains(response, _('Amount'))
        self.assertEqual(AdPaymentTransaction.objects.count(), 0)

        # Note: I've yet to make a complete test for split-payments, as our
        # DummyCyclosBackend uses a constant as the return value for
        # `get_group()`, and setting this within the test won't work due to
        # the request being done via a separate thread(?).


# some qoinware systems override the functionality of the contact name auto
# view, so the tests fail. In these cases, the test move to the custom version
custom_contact_auto = False

try:
    contact_auto_view_2 = resolve(
        reverse('contact_name_auto', kwargs={'community': 1}))
    custom_contact_auto = True
except NoReverseMatch:
    pass

LOG.warning("custom_contact_auto: {0}".format(custom_contact_auto))


class ContactNameAutoTestCase(TestCase):

    def setUp(self):
        activate('en')
        self.community = CC3CommunityFactory.create()

        self.profile_1 = AuthUserProfileFactory.create(community=self.community)
        self.profile_2 = AuthUserProfileFactory.create(community=self.community)
        self.profile_3 = AuthUserProfileFactory.create(community=self.community)

    def tearDown(self):
        activate(settings.LANGUAGE_CODE)

    @skipIf(custom_contact_auto,
            u"Skipped ContactNameAutoTests as custom app being used")
    def test_returned_data(self):
        """
        Tests the JSON data returned by the view.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        # Send a fragment of the string to search for coincidences in the
        # existent profiles. All factory-created profiles have 'CC3Profile' as
        # profile name, so 'CC3' can be a good string to search for.
        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': self.community.pk}
        ), {'contact_name': "CC3", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertIn('pk', data[0])
        self.assertIn('value', data[0])

    @skipIf(custom_contact_auto,
            u"Skipped ContactNameAutoTests as custom app being used")
    def test_dont_return_request_user(self):
        """
        Tests that the request user should not be returned in the search.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': self.community.pk}
        ), {'contact_name': "CC3", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Only return 2 of the 3 created profiles (one is who makes the
        # request).
        self.assertEqual(len(data), 2)

    @skipIf(custom_contact_auto,
            u"Skipped ContactNameAutoTests as custom app being used")
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=False)
    def test_non_existent_community(self):
        """
        Tests returning a 404 error when the user tries to retrieve results
        from a community he doesn't belong to.
        """
        community = CC3CommunityFactory.create()
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': community.pk}
        ), {'contact_name': "CC3", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 404)

    @skipIf(custom_contact_auto,
            u"Skipped ContactNameAutoTests as custom app being used")
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=False)
    def test_invalid_community(self):
        """
        Tests returning a 404 error when the given community is not valid.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': 999}
        ), {'contact_name': "CC3", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 404)

    @skipIf(custom_contact_auto,
            u"Skipped ContactNameAutoTests as custom app being used")
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=False)
    def test_community_results(self):
        """ Only include contacts from own community if
        INTER_COMMUNITIES_TRANSACTIONS==False """
        community = CC3CommunityFactory.create()
        member = AuthUserProfileFactory.create(community=community)

        profile = AuthUserProfileFactory.create(community=community)

        self.client.login(
            username=profile.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': community.pk}
        ), {'contact_name': "CC3", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Must be only 1 user: the one we created above. No users from `setUp`
        # should be present here.
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['pk'], member.pk)

    @skipIf(custom_contact_auto,
            u"Skipped ContactNameAutoTests as custom app being used")
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_results_include_all_communities(self):
        """ Include contacts from all communities if
        INTER_COMMUNITIES_TRANSACTIONS==True """
        community = CC3CommunityFactory.create()

        profile = AuthUserProfileFactory.create(community=community)

        self.client.login(
            username=profile.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': community.pk}
        ), {'contact_name': "CC3", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Must be at least 1 user, created above, plus users from `setUp`
        # should be present here.
        self.assertGreater(len(data), 1)


class TransactionsListViewTestCase(TestCase):

    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.profile = AuthUserProfileFactory.create(web_payments_enabled=True)

        self.url = reverse('accounts_home')

        factory = RequestFactory()
        request = factory.get(self.url)
        request.user = self.profile.user

        self.view = TransactionsListView()
        self.view.request = request
        # Disable pagination for testing view methods. We don't need it now and
        # it's messing with the unit tests.
        self.view.paginate_by = None
        # view assigns object_list to self in 'get', which isn't called by tests
        # so need to set it here to make tests work.
        self.view.object_list = []

    def test_transactions_list_login_required(self):
        """
        Tests login required to access the view.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '{0}?next={1}'.format(reverse('auth_login'), self.url))

    def test_transactions_list_success_get(self):
        """
        Tests successful GET on ``TransactionsListView``.
        """
        self.client.login(
            username=self.profile.user.username, password='testing')
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/accounts_home.html')

    @patch('cc3.cyclos.services.Accounts.search_transfer_types')
    @patch('cc3.cyclos.backends.get_account_status')
    def test_transactions_list_get_context_data(
            self, transactions_mock, search_mock):
        """
        Tests ``get_context_data`` method to ensure that it adds the proper
        context variables.
        """
        # Set the normal Cyclos backend for this test. Will be mocked below.
        set_backend(CyclosBackend())

        # Mocking the `get_account_status` response.
        account_status = MagicMock()
        account_status.accountStatus.availableBalance = Decimal('100')
        transactions_mock.return_value = account_status
        search_mock.return_value = None

        context = self.view.get_context_data(object_list=[])

        self.assertIn('available_balance', context)
        self.assertEqual(context['available_balance'], Decimal('100'))

    @patch('cc3.cyclos.services.Accounts.search_transfer_types')
    @patch('cc3.cyclos.backends.get_account_status')
    def test_transactions_list_get_context_data_account_not_found(
            self, transactions_mock, search_mock):
        """
        Tests ``get_context_data`` method returning ``None`` when the profile
        account was not found in Cyclos backend.
        """
        # Set the normal cyclos backend for this test. Will be mocked below.
        set_backend(CyclosBackend())

        # Mocking a ``AccountNotFoundException`` from Cyclos.
        effect = AccountNotFoundException
        transactions_mock.side_effect = effect
        search_mock.return_value = None

        context = self.view.get_context_data(object_list=[])

        self.assertIsNone(context['available_balance'])

    @patch('cc3.cyclos.services.Accounts.search_transfer_types')
    @patch('cc3.cyclos.backends.get_account_status')
    def test_transactions_list_get_context_data_member_not_found(
            self, transactions_mock, search_mock):
        """
        Tests ``get_context_data`` method returning ``None`` when the member
        profile was not found in Cyclos backend.
        """
        # Set the normal cyclos backend for this test. Will be mocked below.
        set_backend(CyclosBackend())

        # Mocking a ``MemberNotFoundException`` from Cyclos.
        effect = MemberNotFoundException
        transactions_mock.side_effect = effect
        search_mock.return_value = None

        context = self.view.get_context_data(object_list=[])

        self.assertIsNone(context['available_balance'])

    @patch('cc3.cyclos.services.Accounts.search_transfer_types')
    @patch('cc3.cyclos.backends.transactions')
    def test_transactions_list_get_queryset_account_not_found(
            self, transactions_mock, search_mock):
        """
        Tests ``get_queryset`` method returning ``None`` when the profile
        account was not found in Cyclos backend.
        """
        # Set the normal cyclos backend for this test. Will be mocked below.
        set_backend(CyclosBackend())

        # Mocking a ``AccountNotFoundException`` from Cyclos.
        effect = AccountNotFoundException
        transactions_mock.side_effect = effect
        search_mock.return_value = None

        self.assertIsNone(self.view.get_queryset())


class TransactionsSearchListViewTestCase(TestCase):
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.profile = AuthUserProfileFactory.create(web_payments_enabled=True)

        self.url = reverse('accounts_transactions_search')

        factory = RequestFactory()
        request = factory.get(self.url)
        request.user = self.profile.user

        self.view = TransactionsSearchListView()
        self.view.request = request
        # Disable pagination for testing view methods. We don't need it now and
        # it's messing with the unit tests.
        self.view.paginate_by = None
        # view assigns object_list to self in 'get', which isn't called by tests
        # so need to set it here to make tests work.
        self.view.object_list = []

    def test_transactions_search_login_required(self):
        """
        Tests login required to access the view.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '{0}?next={1}'.format(reverse('auth_login'), self.url))

    def test_transactions_list_get_context_data(self):
        """
        Tests ``get_context_data`` method to ensure that it adds the proper
        context variables.
        """
        context = self.view.get_context_data(object_list=[])
        self.assertIn('menu_form', context)
        self.assertIsInstance(context['menu_form'], TransactionsSearchForm)


class PayDirectFormViewTestCase(TestCase):
    def setUp(self):
        self.url = reverse('accounts_pay_direct')

        self.community = CC3CommunityFactory.create()
        self.profile = AuthUserProfileFactory.create(community=self.community)

        factory = RequestFactory()
        request = factory.get(self.url)
        request.user = self.profile.user

        self.view = PayDirectFormView()
        self.view.request = request

    def test_get_form_normal_payment(self):
        """
        Tests the ``get_form`` method in a successful return for a normal user.
        """
        form = self.view.get_form(None)

        self.assertIsInstance(form, TradeQoinPayDirectForm)

    @patch('cc3.cyclos.models.account.CC3Profile.split_payments_allowed')
    def test_get_form_split_payment(self, mock):
        """
        Tests the ``get_form`` method in a successful return for a user allowed
        to do split payments.
        """
        # Mock the response of the `split_payments_allowed` to `True`.
        mock.return_value = True

        form = self.view.get_form(None)

        self.assertIsInstance(form, TradeQoinSplitPayDirectForm)

    def test_get_form_no_payments_allowed(self):
        """
        Tests the ``get_form`` method returning ``None`` when the request user
        is not able to perform any web payments.
        """
        # Create a profile with payments disabled
        profile = AuthUserProfileFactory.create(web_payments_enabled=False)
        self.view.request.user = profile.user

        form = self.view.get_form(None)

        self.assertIsNone(form)

    def test_get_form_user_without_profile(self):
        """
        Tests the ``get_form`` method returning ``None`` when the request user
        dos not have any profile related.
        """
        # Create a raw user for the request, without any profile.
        user = UserFactory.create()

        self.view.request.user = user

        form = self.view.get_form(None)

        self.assertIsNone(form)
