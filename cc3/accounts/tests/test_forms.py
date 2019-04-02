# encoding: utf-8
from datetime import date, timedelta
from decimal import Decimal
from unittest.case import skip

from django import forms
from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.translation import activate, deactivate, ugettext as _

from mock import MagicMock, patch

from cc3.cyclos.tests.test_factories import CC3ProfileFactory
from ..forms import TransactionsSearchForm, TradeQoinPayDirectForm


class TradeQoinPayDirectFormTestCase(TestCase):
    def setUp(self):
        self.profile_1 = CC3ProfileFactory.create()
        self.profile_2 = CC3ProfileFactory.create()
        self.form = TradeQoinPayDirectForm(user=self.profile_1.user)

        self.form.cleaned_data = {
            'amount': Decimal('10'),
            'contact_name': self.profile_2.full_name,
            'profile': self.profile_2,
            'description': 'Testing payments form.'
        }

        activate('en')

    def tearDown(self):
        activate(settings.LANGUAGE_CODE)

    @override_settings(CC3_CURRENCY_INTEGER_ONLY=True, CC3_CURRENCY_MINIMUM=1)
    def test_clean_integer_minimum_amount(self):
        """
        Tests the ``clean_amount`` method when an integer value is set up in
        settings for ``CC3_CURRENCY_MINIMUM``
        and ``CC3_CURRENCY_INTEGER_ONLY`` is True.
        """
        self.form.cleaned_data['amount'] = Decimal('6.35')

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'Only integer amounts are allowed.'),
            self.form.clean_amount)

    @override_settings(CC3_CURRENCY_INTEGER_ONLY=False,
                       CC3_CURRENCY_MINIMUM=0.01)
    def test_clean_amount_minimum_amount(self):
        """
        Tests the ``clean_amount`` method when
        ``CC3_CURRENCY_INTEGER_ONLY`` is False.
        """
        self.form.cleaned_data['amount'] = Decimal('0.00')

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'Only amounts greater or equal to 0.01 are allowed.'),
            self.form.clean_amount)

    def test_clean_description_max_characters(self):
        """
        Tests the validation of the ``description`` field to ensure that only
        allows 180 characters as maximum.
        """
        # Put a 612 characters text as a description.
        self.form.cleaned_data['description'] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecenas"
            " posuere erat vitae erat facilisis posuere. Proin quis turpis "
            "nunc. Nulla tincidunt ante eget magna dignissim maximus. Cras a "
            "odio congue justo mattis efficitur at sed purus. Phasellus non "
            "lorem id enim viverra accumsan id sit amet mi. Pellentesque a "
            "ullamcorper ex. Nunc id feugiat turpis. Etiam ac auctor urna, at "
            "convallis urna. Cras aliquam justo at aliquam posuere. Nam "
            "convallis congue sapien, ut eleifend nunc convallis sit amet. "
            "Curabitur eu odio vehicula elit consectetur sodales. Suspendisse "
            "eget nisl et leo blandit efficitur.")

        self.assertRaises(
            forms.ValidationError,
            self.form.fields['description'].clean,
            self.form.cleaned_data['description'])

    @patch('cc3.cyclos.backends.get_account_status')
    def test_clean_amount_available_balance(self, mock):
        """
        Tests the ``clean_amount`` raises ``ValidationError`` if the amount is
        greater than the available balance for the user.
        """
        self.form.cleaned_data = {
            'amount': Decimal('1000'),
            'contact_name': self.profile_2.full_name,
            'profile': self.profile_2,
            'description': 'Testing payments form.'
        }

        # Mocking the ``get_account_status`` Cyclos backend method.
        # Asking the Cyclos backend for the account balance will return 100,
        # which makes impossible to pay 1000.
        account_status = MagicMock()
        account_status.accountStatus.availableBalance = Decimal('100')
        mock.return_value = account_status

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'You do not have sufficient credit to complete the payment'),
            self.form.clean_amount)

    @override_settings(CYCLOS_PENDING_MEMBERS_CAN_PAY=False)
    @patch('cc3.cyclos.models.account.CC3Profile.has_full_account')
    def test_clean_profile_pending_account(self, mock):
        """
        Tests the ``clean_profile`` method raises ``ValidationError`` if the
        member to be paid belongs to a pending account.
        """
        self.form.cleaned_data = {
            'amount': Decimal('10'),
            'contact_name': self.profile_2.full_name,
            'profile': self.profile_2,
            'description': 'Testing payments form.'
        }
        mock.return_value = False

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'You cannot pay this member as their account is still pending.'),
            self.form.clean_profile)


class TransactionsSearchFormTestCase(TestCase):
    def setUp(self):
        self.form = TransactionsSearchForm()

        activate('en')

    def tearDown(self):
        deactivate()

    def test_clean_from_date(self):
        """
        Tests dates checking in ``clean_from_date`` form method. Must raise a
        ``ValidationError`` if the ``from_date`` field contains a date in the
        future.
        """
        self.form.cleaned_data = {
            # From next month to today - wrong!
            'from_date': date.today() + timedelta(days=30),
            'to_date': date.today()
        }

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'Please enter a date in the past'),
            self.form.clean_from_date)

    def test_clean_to_date(self):
        """
        Tests dates checking in ``clean_to_date`` form method. Must raise a
        ``ValidationError`` if the ``to_date`` field contains a date in the
        future.
        """
        self.form.cleaned_data = {
            # From today to next month - wrong!
            'to_date': date.today() + timedelta(days=30),
            'from_date': date.today()
        }

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'Please enter a date in the past'),
            self.form.clean_to_date)

    @skip("TODO: check empty dates are actually OK")
    def test_clean_no_dates(self):
        """
        Tests the ``clean`` method for the dates checking. The form must
        contain at least one date.
        """
        self.form.cleaned_data = {
        }

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'Please complete at least one search field'),
            self.form.clean)

    def test_clean_invalid_dates(self):
        """
        Tests the ``clean`` method for the dates checking. The 'from' date
        must always be in the past of 'to' date.
        """
        self.form.cleaned_data = {
            # From today to next month - wrong!
            'from_date': date.today() - timedelta(days=10),
            'to_date': date.today() - timedelta(days=30)
        }

        self.assertRaisesMessage(
            forms.ValidationError,
            _(u'The from date is after the to date. Please correct'),
            self.form.clean)
