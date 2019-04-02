from collections import namedtuple, Mapping

from django.utils.translation import ugettext_lazy as _


def namedtuple_with_defaults(typename, field_names, default_values=[]):
    T = namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T


class TransactionException(Exception):
    pass


class AccountException(Exception):
    pass


class NotUniqueException(Exception):
    pass


Transaction = namedtuple_with_defaults(
    'Transaction',
    [
        'sender',
        'recipient',
        'amount',
        'created',
        'description',
        'transfer_id',
        'transfer_type_id'  # optional
    ]
)

NewMember = namedtuple_with_defaults(
    'NewMember',
    [
        'id',
        'username',
        'awaitingEmailValidation'
    ]
)

AccountStatus = namedtuple_with_defaults(
    'AccountStatus',
    [
        'balance',
        'formattedBalance',
        'availableBalance',
        'formattedAvailableBalance',
        'reservedAmount',
        'formattedReservedAmount',
        'creditLimit',
        'formattedCreditLimit',
        'upperCreditLimit',
        'formattedUpperCreditLimit'
    ]
)

AccountHistory = namedtuple_with_defaults(
    'AccountHistory',
    [
        'accountStatus',
        'currentPage',
        'totalCount',
        'transfers'
    ]
)


SUGAR_STATUS_NEW = 'new'
SUGAR_STATUS_UPDATED = 'updated'
SUGAR_STATUS_COMPLETED = 'closed'

SUGAR_STATUS_DICT = {
    SUGAR_STATUS_NEW: _('New'),
    SUGAR_STATUS_UPDATED: _('Updated'),
    SUGAR_STATUS_COMPLETED: _('Closed'),
}
