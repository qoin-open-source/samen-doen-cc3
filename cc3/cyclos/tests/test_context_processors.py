from decimal import Decimal

from django.test import TestCase
from django.test.client import RequestFactory

from mock import MagicMock, patch

from cc3.cyclos.tests.test_factories import CC3ProfileFactory
from cc3.cyclos.common import AccountStatus
from cc3.cyclos.context_processors import balance
from cc3.cyclos.services import MemberNotFoundException


class BalanceTestCase(TestCase):
    """
    Test case for the ``balance`` context processor.
    """
    def setUp(self):
        self.profile = CC3ProfileFactory.create()

        self.factory = RequestFactory()

        self.request = self.factory.get('/')
        self.request.user = self.profile.user

    @patch('cc3.cyclos.backends.get_account_status')
    def test_member_not_found(self, mock):
        """
        Tests the ``balance`` context processor response when member account is
        not found in Cyclos backend.
        """
        # Mocking a ``MemberNotFoundException`` from Cyclos.
        effect = MemberNotFoundException
        mock.side_effect = effect

        data = balance(self.request)
        self.assertDictEqual(data, {
            'balance': None,
            'has_account': False,
            'upper_credit_limit': None,
            'lower_credit_limit': None
        })

    @patch('cc3.cyclos.backends.get_account_status')
    def test_balance_successful(self, mock):
        """
        Tests returned data from ``balance`` context processor when everything
        is okay in Cyclos backend.
        """
        # Mocking the return value to simulate a nice response from Cyclos.
        account_status = MagicMock()
        account_status.accountStatus = AccountStatus(
            balance=Decimal('150.45'),
            formattedBalance='150.45 P',
            availableBalance=Decimal('20000.67'),
            formattedAvailableBalance='20.000,67 P',
            reservedAmount=Decimal('0.00'),
            formattedReservedAmount='0,00 P',
            creditLimit=Decimal('1000000.00'),
            formattedCreditLimit='1.000.000,00 P',
            upperCreditLimit=None,
            formattedUpperCreditLimit=None
        )
        mock.return_value = account_status

        data = balance(self.request)
        self.assertDictEqual(data, {
            'balance': Decimal('150.45'),
            'has_account': True,
            'upper_credit_limit': None,
            'lower_credit_limit': 1000000
        })
