from decimal import Decimal
import datetime

from factory.fuzzy import FuzzyInteger

from cc3.cyclos.common import (
    NewMember, Transaction, AccountStatus, AccountHistory)

CYCLOS_GROUP_ID = 15
USER_PAYMENT_TRANSACTION_ID = '12345'


class DummyCyclosBackend(object):
    """
    A dummy backend to replace the default CyclosBackend, so we can test the
    site without interacting with Cyclos.

    Each call returns valid data, where possible linked to the input given.
    """
    dummy_group_id = CYCLOS_GROUP_ID
    #dummy_member_id = FuzzyInteger(1, 99999).fuzz()
    dummy_name = 'Test account'
    dummy_email = 'test@example.com'
    dummy_username = 'testaccount'

    def __init__(self):
        self.member_group_id = self.dummy_group_id

        # Cache a list of all current performed transactions, if any.
        self.transactions_list = []

    def new(self, username, name, email, business_name, initial_group_id,
            community_code=None, extra_fields=None):
        """ returns a NewMember namedtuple """
        dummy_member_id = FuzzyInteger(1, 99999).fuzz()
        return NewMember(id=dummy_member_id, username=username,
                         awaitingEmailValidation=False)

    def update(self, id, name, email, business_name, community_code=None,
               extra_fields=None):
        pass

    def update_group(self, id, new_group_id, comments):
        pass

    def search(self, currentPage=None, pageSize=None, username=None, name=None,
               email=None, randomOrder=False, groupIds=None,
               groupFilterIds=None, fields=None, showCustomFields=None,
               showImages=None):
        """ returns a list of tuples """
        dummy_member_id = FuzzyInteger(1, 99999).fuzz()
        return [(dummy_member_id, self.dummy_name, self.dummy_email,
                 self.dummy_username, self.dummy_group_id)]

    def user_payment(self, sender, receiver, amount, description,
                     transfer_type_id=None, custom_fields=None):
        # allow for custom transfer type ids
        if transfer_type_id is None:
            transfer_type_id = USER_PAYMENT_TRANSACTION_ID

        transaction = Transaction(
            sender, receiver, amount, datetime.datetime.now(), description,
            transfer_type_id)

        # Add the payment to the list of transactions.
        self.transactions_list += [transaction]

        return transaction

    def get_account_status(self, username):
        account_status = AccountStatus(
            Decimal('100.00'), '100.00',
            Decimal('100.00'), '100.00',
            Decimal('0.00'), '0.00',
            Decimal('50.00'), '50.00',  # Credit limit: 50.-
            Decimal('0.00'), '0.00')
        return AccountHistory(account_status, 1, 1, [])

    def transactions(self, username=None, description=None, from_to=None,
                     from_date=None, to_date=None, direction=None,
                     community=None, account_type_id=None, currency=None):
        # Return the current transactions list.
        return self.transactions_list

    def get_group(self, email):
        return self.dummy_group_id

    def get_member_group_id(self):
        return self.dummy_group_id

    def to_system_payment(self, sender, amount, description, transfer_type_id):
        return Transaction(sender, 'system', amount, datetime.datetime.now(),
                           description, USER_PAYMENT_TRANSACTION_ID)

    def from_system_payment(self, sender, amount, description, transfer_type_id):
        return Transaction(sender, 'system', amount, datetime.datetime.now(),
                           description, USER_PAYMENT_TRANSACTION_ID)
