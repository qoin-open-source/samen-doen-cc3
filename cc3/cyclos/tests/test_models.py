from datetime import date, timedelta
from unittest import skipIf

from django.conf import settings
from django.core import mail
from django.db import IntegrityError
from django.db.models.signals import post_save
from django.test import TestCase
from django.test.utils import override_settings

from mock import patch

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.mail.models import (
    MAIL_TYPE_LARGE_BALANCE_USER, MAIL_TYPE_LARGE_BALANCE_ADMINS,
    MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_USER,
    MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_ADMINS,
    MAIL_TYPE_NEGATIVE_BALANCE_USER, MAIL_TYPE_NEGATIVE_BALANCE_ADMINS)

from ..models import CC3Profile, CyclosAccount
from ..models.account import link_account, notify_community_admins, UserStatusChangeHistory
from .test_factories import (
    CC3CommunityFactory, CC3ProfileFactory, CyclosAccountFactory,
    CyclosGroupFactory, CyclosGroupSetFactory, UserFactory,
    MailMessageFactory)


class CyclosAccountTestCase(TestCase):
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        # Initialize Cyclos groups and groupsets for communities.
        admin_user = UserFactory.create(
            is_staff=True, is_active=True, is_superuser=True)
        self.cyclos_group = CyclosGroupFactory.create(
            initial=True, invoice_user=admin_user)
        cyclos_groupset = CyclosGroupSetFactory.create(
            groups=[self.cyclos_group])
        community = CC3CommunityFactory.create(groupsets=[cyclos_groupset])

        self.profile_1 = CC3ProfileFactory.create(
            web_payments_enabled=True, community=community)
        self.profile_2 = CC3ProfileFactory.create(
            web_payments_enabled=True, community=community)

        # Create the ``CyclosAccount``, with all the groups + groupsets ready.
        self.cyclos_account = CyclosAccountFactory.create(
            cc3_profile=self.profile_1)

    @override_settings(CC3_PROFILE_FIELDS_TO_CYCLOS={})
    @patch('cc3.cyclos.backends.update')
    def test_update_cyclos_on_saving_existent(self, mock):
        """
        Tests updating the account in Cyclos when saving an existent account.

        By using Python Mock library, we ensure that Django-Cyclos SOAP backend
        function ``backends.update`` is called (and, with the right parameters)
        whenever the ``save()`` method is triggered for a ``CyclosAccount``
        instance which belongs to an existent ``CyclosAccount``.
        """
        self.cyclos_account.save()

        mock.assert_called_with(
            self.cyclos_account.cyclos_id,
            u'{0} {1}'.format(self.cyclos_account.cc3_profile.first_name,
                              self.cyclos_account.cc3_profile.last_name),
            self.cyclos_account.cc3_profile.user.email,
            self.cyclos_account.cc3_profile.business_name,
            self.cyclos_account.cc3_profile.community.code,
            extra_fields={})

    @override_settings(CC3_PROFILE_FIELDS_TO_CYCLOS={'member_broker_id': 'pk'})
    @patch('cc3.cyclos.backends.update')
    def test_update_cyclos_extra_fields(self, mock):
        """
        Tests ``extra_fields`` parameter is correctly built and passed to the
        ``update`` method when saving an existent account.

        The ``extra_fields`` parameter is a Python dictionary built by checking
        the ``CC3_PROFILE_FIELDS_TO_CYCLOS`` setting, a dictionary which maps
        Cyclos database columns with ``CC3Profile`` fields.

        In this test case, we suppose that we want to fill the Cyclos DB field
        ``member_broker_id`` with the ``pk`` of the ``CC3Profile`` instance.
        """
        self.cyclos_account.save()

        mock.assert_called_with(
            self.cyclos_account.cyclos_id,
            u'{0} {1}'.format(self.cyclos_account.cc3_profile.first_name,
                              self.cyclos_account.cc3_profile.last_name),
            self.cyclos_account.cc3_profile.user.email,
            self.cyclos_account.cc3_profile.business_name,
            self.cyclos_account.cc3_profile.community.code,
            extra_fields={
                'member_broker_id': self.cyclos_account.cc3_profile.pk})

    @override_settings(CC3_PROFILE_FIELDS_TO_CYCLOS={})
    @patch('cc3.cyclos.backends.search')
    @patch('cc3.cyclos.backends.new')
    def test_create_cyclos_on_saving_new(self, new_mock, search_mock):
        """
        Tests creating the account in Cyclos when saving a new account.

        By using Python Mock library, we ensure that Django-Cyclos SOAP backend
        function ``backends.new`` is called (and, with the right parameters)
        whenever the ``save()`` method is triggered for a ``CyclosAccount``
        new instance.
        """
        # The ``CyclosBackend.search`` method is called by the
        # ``CyclosAccount.save`` method to look if a Cyclos account was already
        # created for this profile. Thus, we mock it to return an empty search,
        # making it continue forward to send a request to Cyclos.
        search_mock.return_value = []

        # Create the new account.
        CyclosAccount.objects.create(cc3_profile=self.profile_2)

        initial_groups = self.profile_2.community.get_initial_groups(
            self.profile_2.groupset)

        new_mock.assert_called_with(
            self.profile_2.user.username,
            u'{0} {1}'.format(self.profile_2.first_name,
                              self.profile_2.last_name),
            self.profile_2.user.email,
            self.profile_2.business_name,
            initial_groups[0].id,
            community_code=self.profile_2.community.code,
            extra_fields={})

    @patch('cc3.cyclos.backends.search')
    def test_assign_cyclos_on_saving_new(self, mock):
        """
        Tests assigning the Cyclos ID to the ``CyclosAccount.cyclos_id`` field
        in case the user was found in Cyclos as an already existent user when
        trying to create the ``CyclosAccount`` entry.
        """
        mock.return_value = [
            (
                99,  # Let's suppose the user ID in Cyclos DB is '99'.
                '{0} {1}'.format(
                    self.profile_2.first_name, self.profile_2.last_name),
                self.profile_2.user.email,
                self.profile_2.user.username,
                self.cyclos_group.pk
            )
        ]

        CyclosAccount.objects.create(cc3_profile=self.profile_2)

        # Check that the Cyclos ID was successfully assigned.
        account = CyclosAccount.objects.get(cc3_profile=self.profile_2)
        self.assertEqual(account.cyclos_id, 99)

    @override_settings(CC3_PROFILE_FIELDS_TO_CYCLOS={'member_broker_id': 'pk'})
    @patch('cc3.cyclos.backends.search')
    @patch('cc3.cyclos.backends.new')
    def test_create_cyclos_extra_fields(self, new_mock, search_mock):
        """
        Tests ``extra_fields`` parameter is correctly built and passed to the
        ``update`` method when saving a new account.

        In this test case, we suppose that we want to fill the Cyclos DB field
        ``member_broker_id`` with the ``pk`` of the ``CC3Profile`` instance.
        """
        search_mock.return_value = []
        CyclosAccount.objects.create(cc3_profile=self.profile_2)

        initial_groups = self.profile_2.community.get_initial_groups(
            self.profile_2.groupset)

        new_mock.assert_called_with(
            self.profile_2.user.username,
            u'{0} {1}'.format(self.profile_2.first_name,
                              self.profile_2.last_name),
            self.profile_2.user.email,
            self.profile_2.business_name,
            initial_groups[0].id,
            community_code=self.profile_2.community.code,
            extra_fields={'member_broker_id': self.profile_2.pk})

    def test_initial_group_integrity_check(self):
        """
        Tests ``IntegrityError`` raised when trying to save a ``CyclosAccount``
        for a ``CC3Profile`` which ``CC3Community`` does not have any initial
        group defined.
        """
        profile = CC3ProfileFactory.create()

        self.assertRaisesMessage(
            IntegrityError,
            u'Error: no initial CyclosGroup for community {0} defined'.format(
                profile.community),
            CyclosAccount.objects.create,
            cc3_profile=profile)


class CC3ProfileTestCase(TestCase):
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        # Disconnect ``link_account`` signal.
        post_save.disconnect(
            receiver=link_account, sender=CC3Profile,
            dispatch_uid='cc3_qoin_profile_save')

        self.user = UserFactory.create()
        self.cyclos_group = CyclosGroupFactory.create(initial=True)
        self.cyclos_groupset = CyclosGroupSetFactory.create(
            groups=[self.cyclos_group])
        self.community = CC3CommunityFactory.create(
            groupsets=[self.cyclos_groupset])
        self.profile = CC3ProfileFactory.create(community=self.community)

        self.negative_balance_email = MailMessageFactory.create(
            type=MAIL_TYPE_NEGATIVE_BALANCE_USER,
            subject="Negative balance USER(NEG)")
        self.negative_balance_email_admins = MailMessageFactory.create(
            type=MAIL_TYPE_NEGATIVE_BALANCE_ADMINS,
            subject="Negative balance ADMIN(NEG)")
        self.negative_balance_collect_email = MailMessageFactory.create(
            type=MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_USER,
            subject="Negative balance USER(COLLECT)")
        self.negative_balance_collect_email_admins = MailMessageFactory.create(
            type=MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_ADMINS,
            subject="Negative balance ADMIN(COLLECT)")
        self.large_balance_email = MailMessageFactory.create(
            type=MAIL_TYPE_LARGE_BALANCE_USER,
            subject="Large balance USER(LARGE)")
        self.large_balance_email_admins = MailMessageFactory.create(
            type=MAIL_TYPE_LARGE_BALANCE_ADMINS,
            subject="Large balance ADMIN(LARGE)")

    def tearDown(self):
        # Reconnect signal after testing.
        post_save.connect(
            receiver=link_account, sender=CC3Profile,
            dispatch_uid='cc3_qoin_profile_save')

    @override_settings(ADMINS_APPROVE_PROFILES=True)
    def test_save_new_approved_visible(self):
        """
        Tests the ``save`` method setting up the ``is_approved`` field and the
        ``is_visible`` field to ``False`` on new object creation depending on
        the ``ADMINS_APPROVE_PROFILES`` setting.
        """
        cc3_profile = CC3Profile(
            user=self.user,
            first_name='John',
            last_name='Doe',
            business_name='Maykin Media',
            country='NL',
            city='Amsterdam',
            address='Herengracht 416',
            postal_code='1017BZ',
            phone_number='+31 (0)20 753 05 23',
            community=self.community,
            cyclos_group=self.cyclos_group,
            groupset=self.cyclos_groupset
        )
        cc3_profile.save()

        self.assertFalse(cc3_profile.is_approved)
        self.assertFalse(cc3_profile.is_visible)

    @override_settings(ADMINS_APPROVE_PROFILES=True)
    def test_save_existent_approved(self):
        """
        Tests the ``save`` method being triggered after admin approval. The
        ``is_visible`` field must be changed to ``True``.
        """
        profile = CC3ProfileFactory.create(community=self.community)

        self.assertFalse(profile.is_visible)
        self.assertFalse(profile.is_approved)

        profile.is_approved = True
        profile.save()

        self.assertTrue(profile.is_visible)

    def test_name_property_incomplete(self):
        """
        Tests the ``name`` property when trying to show the name of a profile
        which was not completed (``first_name`` and ``last_name`` missing).
        """
        cc3_profile = CC3Profile.objects.create(
            user=self.user,
            country='NL',
            city='Amsterdam',
            address='Herengracht 416',
            postal_code='1017BZ',
            phone_number='+31 (0)20 753 05 23',
            community=self.community,
            cyclos_group=self.cyclos_group,
            groupset=self.cyclos_groupset)

        self.assertEqual(cc3_profile.name, cc3_profile.user.email)

    def test_name_property_complete(self):
        """
        Tests the ``name`` property when the profile is completed.
        """
        self.assertEqual(
            self.profile.name,
            u'{0} {1}'.format(self.profile.first_name, self.profile.last_name))

    def test_full_name_completed(self):
        """
        Tests the ``full_name`` property when the ``business_name`` is filled.
        """
        self.assertEqual(
            self.profile.full_name,
            u'{0} {1} ({2})'.format(
                self.profile.first_name, self.profile.last_name,
                self.profile.business_name))

    def test_full_name_business_missing(self):
        """
        Tests the ``full_name`` property when the ``business_name`` is missing.
        """
        self.profile.business_name = ''
        self.profile.save()

        self.assertEqual(
            self.profile.full_name,
            u'{0} {1}'.format(self.profile.first_name, self.profile.last_name))

    def test_full_name_names_missing(self):
        """
        Tests the ``full_name`` property when there are some name fields not
        filled yet.
        """
        self.profile.first_name = ''
        self.profile.last_name = ''
        self.profile.business_name = ''
        self.profile.save()

        self.assertEqual(self.profile.full_name, u'')

    @patch('cc3.cyclos.backends.get_group')
    def test_get_cyclos_group_no_community(self, mock):
        """
        Tests the ``get_cyclos_group`` method when the user is not a member of
        any community.
        """
        mock.return_value = 15

        self.profile.community = None
        self.profile.save()

        self.assertIsNone(self.profile.get_cyclos_group())

    @patch('cc3.cyclos.backends.get_group')
    def test_get_cyclos_group_initial_groups(self, mock):
        """
        Tests the ``get_cyclos_group`` method when the user a member of a group
        marked as 'initial group'.
        """
        mock.return_value = self.cyclos_group.id

        self.assertEqual(self.profile.get_cyclos_group(), self.cyclos_group)

    @patch('cc3.cyclos.backends.get_group')
    def test_get_cyclos_group_full_groups(self, mock):
        """
        Tests the ``get_cyclos_group`` method when the user is a member of a
        group marked as 'full group'.
        """
        # Now creating a separate 'full' Cyclos group. The testing profile will
        # now be a only member of that group. The mocked Cyclos SOAP API method
        # ``get_group`` will return that Cyclos group ID, so our tested
        # ``get_cyclos_group`` method must return that group.
        cyclos_group = CyclosGroupFactory.create(full=True)
        mock.return_value = cyclos_group.id

        cyclos_groupset = CyclosGroupSetFactory.create(
            groups=[cyclos_group])
        community = CC3CommunityFactory.create(groupsets=[cyclos_groupset])
        self.profile.community = community
        self.profile.cyclos_group = cyclos_group
        self.profile.save()

        self.assertEqual(self.profile.get_cyclos_group(), cyclos_group)

    @patch('cc3.cyclos.backends.get_group')
    def test_sync_cyclos_group(self, mock):
        """
        Tests the ``sync_cyclos_group`` method for a successful Cyclos group
        synchronization.
        """
        # Now creating a separate 'initial' Cyclos group. The testing profile
        # has been initially assigned to another group: ``self.cyclos_group``,
        # but now we are mocking the return value from the Cyclos SOAP API to
        # say that the Cyclos group of that user has changed for the new one.
        # Conclusively, the Cyclos group of the profile in Django DB must be
        # changed according with Cyclos response.
        cyclos_group = CyclosGroupFactory.create(initial=True)
        mock.return_value = cyclos_group.id

        cyclos_groupset = CyclosGroupSetFactory.create(
            groups=[cyclos_group])
        community = CC3CommunityFactory.create(groupsets=[cyclos_groupset])
        self.profile.community = community
        self.profile.save()

        # The method returns ``True`` because it succeeded.
        self.assertTrue(self.profile.sync_cyclos_group())

        # Check that the group has been changed in Django DB.
        self.assertEqual(self.profile.cyclos_group, cyclos_group)

    @patch('cc3.cyclos.backends.get_group')
    def test_sync_cyclos_group_failure_no_group(self, mock):
        """
        Tests the ``sync_cyclos_group`` method when the user does not belong to
        any Cyclos group - then the syncing fails and method returns ``False``.
        """
        # Mock the Cyclos SOAP API response with a non-existent group. This
        # will make the ``get_cyclos_group`` return ``None``, then no group,
        # then ``sync_cyclos_group`` will fail gracefully.
        mock.return_value = 99

        self.assertFalse(self.profile.sync_cyclos_group())

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_track_negative_balance_going_negative(self):
        """
        Tests that track_negative_balance handles balance going negative
        """
        self.profile.negative_balance_start_date = None
        self.profile.save()
        self.profile.track_negative_balance(-100)
        self.assertEqual(self.profile.negative_balance_start_date,
                         date.today())

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_track_negative_balance_already_negative(self):
        """
        Tests that track_negative_balance doesn't update start_date
        if already set
        """
        self.profile.negative_balance_start_date = date(2015, 1, 1)
        self.profile.save()
        self.profile.track_negative_balance(-100)
        self.assertEqual(self.profile.negative_balance_start_date,
                         date(2015, 1, 1))

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_track_negative_balance_goes_negative(self):
        """
        Tests that track_negative_balance handles balance recovering
        """
        self.profile.negative_balance_start_date = date.today()
        self.profile.save()
        self.profile.track_negative_balance(0)
        self.assertEqual(self.profile.negative_balance_start_date,
                         None)
        self.assertEqual(self.profile.negative_balance_warning_sent,
                         None)

    @override_settings(TRACK_NEGATIVE_BALANCES=False)
    def test_track_negative_balance_not_configured(self):
        """
        Tests that track_negative_balance does nothing if the setting
        isn't set
        """
        self.profile.negative_balance_start_date = None
        self.profile.save()
        self.profile.track_negative_balance(-100)
        self.assertEqual(self.profile.negative_balance_start_date,
                         None)

    @override_settings(TRACK_LARGE_BALANCE_LIMIT=2000)
    def test_track_large_balance_exceeded(self):
        """
        Tests that track_large_balance handles balance passing limit
        """
        self.profile.large_balance_start_date = None
        self.profile.save()
        self.profile.track_large_balance(2001)
        self.assertEqual(self.profile.large_balance_start_date,
                         date.today())

    @override_settings(TRACK_LARGE_BALANCE_LIMIT=2000)
    def test_track_large_balance_already_exceeded(self):
        """
        Tests that track_large_balance doesn't update start_date
        if already set
        """
        self.profile.large_balance_start_date = date(2015, 1, 1)
        self.profile.save()
        self.profile.track_large_balance(2001)
        self.assertEqual(self.profile.large_balance_start_date,
                         date(2015, 1, 1))

    @override_settings(TRACK_LARGE_BALANCE_LIMIT=2000)
    def test_track_large_balance_goes_below(self):
        """
        Tests that track_large_balance handles balance recovering
        """
        self.profile.large_balance_start_date = date.today()
        self.profile.save()
        self.profile.track_large_balance(2000)
        self.assertEqual(self.profile.large_balance_start_date,
                         None)

    @override_settings(TRACK_LARGE_BALANCE_LIMIT=None)
    def test_track_large_balance_not_configured(self):
        """
        Tests that track_large_balance does nothing if the setting
        isn't set
        """
        self.profile.large_balance_start_date = None
        self.profile.save()
        self.profile.track_large_balance(3000)
        self.assertEqual(self.profile.large_balance_start_date,
                         None)

    def test_get_date_credit_expires(self):
        """
        Tests get_date_credit_expires
        """
        self.profile.credit_term = 3  # 3 months
        self.profile.negative_balance_start_date = date(2015, 1, 31)
        self.profile.save()
        self.assertEqual(self.profile.get_date_credit_expires(),
                         date(2015, 4, 30))

    def test_get_date_credit_expires_not_negative(self):
        """
        Tests get_date_credit_expires returns None if balance not negative
        """
        self.profile.credit_term = 3  # 3 months
        self.profile.negative_balance_start_date = None
        self.profile.save()
        self.assertEqual(self.profile.get_date_credit_expires(),
                         None)

    def test_get_date_credit_expires_no_credit_term(self):
        """
        Tests get_date_credit_expires returns None if credit_term not set
        """
        self.profile.credit_term = None
        self.profile.negative_balance_start_date = date(2015, 1, 31)
        self.profile.save()
        self.assertEqual(self.profile.get_date_credit_expires(),
                         None)

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_negative_balance_warning_due(self):
        """
        Tests negative_balance_warning_due when true
        """
        self.profile.credit_term = 3
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=60)
        self.profile.negative_balance_warning_sent = None
        self.profile.save()
        self.community.negative_balance_warning_buffer = 60
        self.community.save()
        # credit expires in about a month; warning due about a month ago
        self.assertEqual(
            self.profile.negative_balance_warning_due(), True)

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_negative_balance_warning_not_due(self):
        """
        Tests negative_balance_warning_due when not true
        """
        self.profile.credit_term = 3
        self.profile.negative_balance_start_date = date.today()
        self.profile.negative_balance_warning_sent = None
        self.profile.save()
        self.community.negative_balance_warning_buffer = 30
        self.community.save()
        # credit expires in 3 months; warning due in about a month
        self.assertEqual(
            self.profile.negative_balance_warning_due(), False)

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_negative_balance_warning_can_be_zero(self):
        """
        Tests negative_balance_warning_buffer of zero works
        """
        self.profile.credit_term = 2
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=62)
        self.profile.negative_balance_warning_sent = None
        self.profile.save()
        self.community.negative_balance_warning_buffer = 0
        self.community.save()
        # credit expired about 2 months ago; warning due today or sooner
        self.assertEqual(
            self.profile.negative_balance_warning_due(), True)

    @override_settings(TRACK_NEGATIVE_BALANCES=False)
    def test_negative_balance_warning_due_not_configured(self):
        """
        Tests negative_balance_warning_due return False if not configured
        """
        self.profile.credit_term = 3
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=60)
        self.profile.negative_balance_warning_sent = None
        self.profile.save()
        self.community.negative_balance_warning_buffer = 60
        self.community.save()
        # credit expires in about a month; warning due about a month ago
        # (i.e. would be True if setting configured)
        self.assertEqual(
            self.profile.negative_balance_warning_due(), False)

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_negative_balance_collect_due(self):
        """
        Tests negative_balance_collect_due when true
        """
        self.profile.credit_term = 1
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=66)
        self.profile.negative_balance_collect_sent = None
        self.profile.save()
        self.community.negative_balance_collect_after = 1
        self.community.save()
        # credit expired; collect due a few days ago
        self.assertEqual(
            self.profile.negative_balance_collect_due(), True)

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_negative_balance_collect_not_due(self):
        """
        Tests negative_balance_collect_due when not true
        """
        self.profile.credit_term = 1
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=36)
        self.profile.negative_balance_collect_sent = None
        self.profile.save()
        self.community.negative_balance_collect_after = 1
        self.community.save()
        # credit expired; collect due in about a month
        self.assertEqual(
            self.profile.negative_balance_collect_due(), False)

    @override_settings(TRACK_NEGATIVE_BALANCES=True)
    def test_negative_balance_collect_can_be_zero(self):
        """
        Tests negative_balance_collect_buffer of zero works
        """
        self.profile.credit_term = 2
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=62)
        self.profile.negative_balance_collect_sent = None
        self.profile.save()
        self.community.negative_balance_collect_after = 0
        self.community.save()
        # credit expired about 2 months ago; collect due today or sooner
        self.assertEqual(
            self.profile.negative_balance_collect_due(), True)

    @override_settings(TRACK_NEGATIVE_BALANCES=False)
    def test_negative_balance_collect_due_not_configured(self):
        """
        Tests negative_balance_collect_due return False if not configured
        """
        self.profile.credit_term = 1
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=66)
        self.profile.negative_balance_collect_sent = None
        self.profile.save()
        self.community.negative_balance_collect_after = 1
        self.community.save()
        # credit expired; collect due a few days ago
        # (i.e. would be True if setting configured)
        self.assertEqual(
            self.profile.negative_balance_collect_due(), False)

    def test_send_negative_balance_warning_emails(self):
        """
        Tests that the user and admin emails are sent, and that the
        warning_sent field gets set
        """
        self.profile.credit_term = 3  # 3 months
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=60)
        self.profile.negative_balance_warning_sent = None
        self.community.negative_balance_warning_buffer = 60
        self.community.save()
        self.profile.save()
        self.profile.send_negative_balance_warning_emails()
        self.assertIn("USER(NEG)", mail.outbox[0].subject)
        # TODO: need to create a comm admin for this:
        #self.assertIn("ADMIN(NEG)", mail.outbox[1].subject)
        self.assertEqual(
            self.profile.negative_balance_warning_sent, date.today())

    def test_send_negative_balance_collect_emails(self):
        """
        Tests that the user and admin collect emails are sent, and that the
        collect_sent field gets set
        """
        self.profile.credit_term = 1  # 1 months
        self.profile.negative_balance_start_date = \
            date.today() - timedelta(days=66)
        self.profile.negative_balance_collect_sent = None
        self.community.negative_balance_collect_after = 1
        self.community.save()
        self.profile.save()
        self.profile.send_negative_balance_collect_emails()
        self.assertIn("USER(COLLECT)", mail.outbox[0].subject)

        # TODO: need to create a comm admin for this:
        # self.assertIn("ADMIN(COLLECT)", mail.outbox[1].subject)
        self.assertEqual(
            self.profile.negative_balance_collect_sent, date.today())

    def test_send_large_balance_emails(self):
        """
        Tests that the user and admin emails are sent
        """
        self.profile.send_large_balance_emails(2000, 1000)
        self.assertIn("USER(LARGE)", mail.outbox[0].subject)

        # TODO: need to create a comm admin for this:
        # self.assertIn("ADMIN(LARGE)", mail.outbox[1].subject)

    @skipIf(settings.AUTH_PROFILE_MODULE != 'cyclos.CC3Profile',
            u'Skipped as AUTH_PROFILE_MODULE not cyclos.CC3Profile')
    def test_update_first_login_state(self):
        """
        Tests that before logging in, cc3 profile first_login is None, and
        after first login it is True. Lastly, after second login, it is False
        """
        test_user = UserFactory.create()
        test_profile = CC3ProfileFactory.create(
            user=test_user, community=self.community)

        self.assertEqual(test_profile.first_login, None)
        self.client.login(
            username=test_profile.user.username, password='testing')

        self.assertEqual(test_profile.first_login, True)
        self.client.logout()

        self.client.login(
            username=test_profile.user.username, password='testing')
        self.assertEqual(test_profile.first_login, False)

'''
class UserStatusChangeHistoryTestCase(TestCase):
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.cyclos_group = CyclosGroupFactory.create(initial=True)
        self.cyclos_groupset = CyclosGroupSetFactory.create(
            groups=[self.cyclos_group])
        self.community = CC3CommunityFactory.create(
            groupsets=[self.cyclos_groupset])

        # Disconnect ``notify_community_admins`` signal.
        post_save.disconnect(
            receiver=notify_community_admins, sender=CC3Profile,
            dispatch_uid='cc3_qoin_new_profile_notify')

    def tearDown(self):
        # Reconnect signal after testing.
        post_save.connect(
            receiver=notify_community_admins, sender=CC3Profile,
            dispatch_uid='cc3_qoin_new_profile_notify')

    def test_user_status_change_history_deactivate_reactivate(self):
        test_user = UserFactory.create()

        self.assertEqual(test_user.is_active, True)
        test_user.is_active = False
        test_user.save()

        test_user.is_active = True
        test_user.save()

        history = UserStatusChangeHistory.objects.filter(user=test_user)
        self.assertEqual(history.count(), 2)

        if history.count() == 2:
            log_entry = history[0]
            self.assertEquals(log_entry.activate, False)
            self.assertEquals(log_entry.change_author, None)

            log_entry = history[1]
            self.assertEquals(log_entry.activate, True)
            self.assertEquals(log_entry.change_author, None)

    def test_user_status_change_history_no_change(self):
        test_user = UserFactory.create()
        self.assertEqual(test_user.is_active, True)

        test_user.is_active = False
        test_user.save()

        test_user.first_name = 'JOHN'
        test_user.is_active = False
        test_user.save()

        history = UserStatusChangeHistory.objects.filter(user=test_user)
        self.assertEqual(history.count(), 1)

        if history.count() == 1:
            log_entry = history[0]
            self.assertEquals(log_entry.activate, False)
            self.assertEquals(log_entry.change_author, None)

    def test_user_status_change_history_close_account(self):
        test_user = UserFactory.create()
        test_profile = CC3ProfileFactory.create(
            user=test_user, community=self.community)
        self.assertEqual(test_user.is_active, True)

        test_profile.close_account()

        history = UserStatusChangeHistory.objects.filter(user=test_user)
        self.assertEqual(history.count(), 1)

        if history.count() == 1:
            log_entry = history[0]
            self.assertEquals(log_entry.activate, False)
            self.assertEquals(log_entry.change_author, None)'''








