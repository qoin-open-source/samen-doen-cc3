"""
Replace this with more appropriate tests for your application.
"""

from unittest.case import skip

from django.test import TestCase
from django.conf import settings

from cc3.cyclos import backends
from cc3.cyclos.common import *
import cc3

import uuid
from decimal import Decimal
from string import ascii_letters, digits
import datetime

USER_GROUP_ID = 15


def get_username():
    """
    Generate a short unique username.
    Strip it of anything other than letters and digits - see services.register
    """
    username = uuid.uuid4().bytes.encode('base64').rstrip('=\n')
    username = "".join([ch for ch in username if ch in (
        ascii_letters + digits)])
    return username


class RegisterTests(TestCase):

    @skip('To be reviewed...')
    def test_new(self):
        """
        Test registration of a new user
        There is no API in cyclos for deleting users so we need to create
        unique id's each time.
        """
        username = get_username()
        member = backends.new(
            username, 'Tester McTest', username + '@example.com',
            'Test Business', USER_GROUP_ID)

        self.assertEqual(member.username, username)
        self.assertTrue(isinstance(member.id, long))
        self.assertFalse(member.awaitingEmailValidation)

    @skip('To be reviewed...')
    def test_new_duplicate_username(self):
        username = get_username()
        member = backends.new(
            username, 'Tester McTest', username + '@example.com',
            'Test Business', USER_GROUP_ID)

        self.assertEqual(member.username, username)

        # TODO: we could really use a custom exception here
        self.assertRaises(NotUniqueException, backends.new,
                          username,
                          'Tester McTest',
                          username + '@example.com',
                          'Test Business',
                          USER_GROUP_ID)

    def test_new_duplicate_email(self):
        # TODO: what about other fields e.g. email?
        pass

    def test_long_username(self):
        # TODO: username limit is 30 characters
        # add test for a long username
        pass


class UpdateTests(TestCase):

    @skip('To be reviewed...')
    def test_update(self):
        # register a new user to update
        username = get_username()
        name = 'Tester McTest'
        member = backends.new(username,
                              name,
                              username + '@example.com',
                              'Test Business',
                              USER_GROUP_ID)

        _id = member.id

        results = backends.search(username=username)
        self.assertEqual(results[0][1], name)

        newname = 'New name'
        backends.update(
            _id, newname, username + '@example2.com', 'New business')

        results = backends.search(username=username)
        self.assertEqual(results[0][1], newname)

    def test_not_found(self):
        # TODO
        pass


class PaymentTests(TestCase):

    def _set_credit_limit(self, email, amount):
        """ an awful hack to set the user's credit limit as there is
        no API for this """
        if isinstance(backends.get_backend(),
                      cc3.cyclos.transactions.CyclosBackend):
            import _mysql

            dbsettings = settings.REMOTE_DATABASES['cyclos']
            db = _mysql.connect(dbsettings['HOST'], dbsettings['USER'],
                                dbsettings['PASSWORD'], dbsettings['NAME'])

            db.query("SELECT id FROM members WHERE email = '%s'" % (email, ))
            result = db.store_result()
            row = result.fetch_row(maxrows=1)
            _id = row[0][0]

            db.query("UPDATE accounts SET credit_limit = %s "
                     "WHERE member_id = %s" % (amount, _id,))

    @skip('To be reviewed...')
    def test_user_payment_not_enough_credit(self):
        # create two users to transact between
        sender = get_username()
        member = backends.new(
            sender, 'Sender', sender + '@example.com', 'Test Business',
            USER_GROUP_ID)
        self.assertIsNotNone(member)
        receiver = get_username()
        member = backends.new(
            receiver, 'Receiver', receiver + '@example.com', 'Test Business',
            USER_GROUP_ID)
        self.assertIsNotNone(member)

        try:
            transaction = backends.user_payment(
                sender, receiver, 10.00, 'a test transaction')
            self.assertIsNotNone(transaction)

            self.assertTrue(False)
        except TransactionException as e:
            self.assertTrue(e.args[0].find('NOT_ENOUGH_CREDITS') >= 0)

    @skip('To be reviewed...')
    def test_user_payment(self):
        # create two users to transact between
        sender = get_username()
        email = sender + '@example.com'
        member = backends.new(
            sender, 'Sender', email, 'Test Business', USER_GROUP_ID)
        self.assertIsNotNone(member)
        self._set_credit_limit(email, 10000.0)

        receiver = get_username()
        member = backends.new(
            receiver, 'Receiver', receiver + '@example.com', 'Test Business',
            USER_GROUP_ID)
        self.assertIsNotNone(member)

        amount = 10.00
        description = 'a test transaction'
        transaction = backends.user_payment(
            sender, receiver, amount, description)

        self.assertEqual(transaction.sender, sender)
        self.assertEqual(transaction.recipient, receiver)
        self.assertEqual(transaction.amount, Decimal(amount))
        self.assertEqual(transaction.description, description)
        self.assertIsInstance(transaction.created, datetime.datetime)

    # def test_system_donation(self):
    #     receiver = get_username()
    #     member = backends.new(receiver,
    #                            'Receiver',
    #                            receiver + '@example.com',
    #                            'Test Business',
    #                            USER_GROUP_ID)

    #     amount = 10.00
    #     description = 'a test transaction'
    #     transaction = backends.system_donation(receiver, amount)

    #     self.assertEqual(transaction.sender, sender)
    #     self.assertEqual(transaction.recipient, receiver)
    #     self.assertEqual(transaction.amount, Decimal(amount))
    #     self.assertEqual(transaction.description, description)
    #     self.assertIsInstance(transaction.created, datetime.datetime)

    @skip('To be reviewed...')
    def test_account_status(self):
        sender = get_username()
        email = sender + '@example.com'
        member = backends.new(
            sender, 'Sender', email, 'Test Business', USER_GROUP_ID)
        self.assertIsNotNone(member)
        receiver = get_username()
        member = backends.new(
            receiver, 'Receiver', receiver + '@example.com', 'Test Business',
            USER_GROUP_ID)
        self.assertIsNotNone(member)

        # test initial account status
        status = backends.get_account_status(sender)

        self.assertEqual(status.accountStatus.balance, Decimal('0'))
        self.assertEqual(status.accountStatus.availableBalance, Decimal('0'))
        self.assertEqual(status.accountStatus.reservedAmount, Decimal('0'))
        self.assertEqual(status.accountStatus.creditLimit, Decimal('0'))
        self.assertIsNone(status.accountStatus.upperCreditLimit)

        status = backends.get_account_status(receiver)

        self.assertEqual(status.accountStatus.balance, Decimal('0'))
        self.assertEqual(status.accountStatus.availableBalance, Decimal('0'))
        self.assertEqual(status.accountStatus.reservedAmount, Decimal('0'))
        self.assertEqual(status.accountStatus.creditLimit, Decimal('0'))
        self.assertIsNone(status.accountStatus.upperCreditLimit)

        # set credit limit
        limit = 10000.0
        self._set_credit_limit(email, limit)

        status = backends.get_account_status(sender)

        self.assertEqual(status.accountStatus.balance, Decimal('0'))
        self.assertEqual(status.accountStatus.availableBalance, Decimal(limit))
        self.assertEqual(status.accountStatus.reservedAmount, Decimal('0'))
        self.assertEqual(status.accountStatus.creditLimit, Decimal(limit))
        self.assertIsNone(status.accountStatus.upperCreditLimit)

        # transact
        amount = 10.00
        description = 'a test transaction'
        transaction = backends.user_payment(
            sender, receiver, amount, description)
        self.assertIsNotNone(transaction)
        status = backends.get_account_status(sender)

        self.assertEqual(status.accountStatus.balance, Decimal(amount * -1.0))
        self.assertEqual(status.accountStatus.availableBalance,
                         Decimal(limit-amount))
        self.assertEqual(status.accountStatus.reservedAmount, Decimal('0'))
        self.assertEqual(status.accountStatus.creditLimit, Decimal(limit))
        self.assertIsNone(status.accountStatus.upperCreditLimit)

        status = backends.get_account_status(receiver)

        self.assertEqual(status.accountStatus.balance, Decimal(amount))
        self.assertEqual(status.accountStatus.availableBalance,
                         Decimal(amount))
        self.assertEqual(status.accountStatus.reservedAmount, Decimal('0'))
        self.assertEqual(status.accountStatus.creditLimit, Decimal('0'))
        self.assertIsNone(status.accountStatus.upperCreditLimit)
