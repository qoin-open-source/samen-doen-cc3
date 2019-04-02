"""Backends for the credits/payments/transactions system"""
from cc3.cyclos.transactions import CyclosBackend

_backend = None


def get_backend():
    global _backend
    if _backend is None:
        _backend = CyclosBackend()
    return _backend


def set_backend(backend):
    global _backend
    _backend = backend


def new(username, name, email, business_name, initial_group_id,
        community_code=None, extra_fields=None):
    """
    Create a new account.

    :Returns:
        a NewMember namedtuple
    """
    return get_backend().new(
        username, name, email, business_name, initial_group_id, community_code,
        extra_fields)


def update(_id, name, email, business_name, community_code=None,
           extra_fields=None):
    """ Update account details. """
    return get_backend().update(
        _id, name, email, business_name, community_code, extra_fields)


def update_group(_id, new_group_id, comments):
    """
    Update member's group.

    :param id: The user ID in Cyclos - an integer number.
    :param new_group_id: The group ID of the group to which the user will be
    assigned.
    :param comments: A mandatory comment (string) for the reason of the group
    change.
    :return: The result of the ``CyclosBackend.update_group`` method.
    """
    return get_backend().update_group(_id, new_group_id, comments)


def search(currentPage=None, pageSize=None,
           username=None, name=None, email=None,
           randomOrder=False, groupIds=None, groupFilterIds=None, fields=None,
           showCustomFields=None, showImages=None):
    """
    Search for a member.

    :return: a list of tuples (id, name, email, username, group_id)
    """
    # TODO: Result should probably be a namedtuple for consistency.
    return get_backend().search(currentPage, pageSize,
                                username, name, email,
                                randomOrder, groupIds, groupFilterIds, fields,
                                showCustomFields, showImages)


def user_payment(sender, receiver, amount, description,
                 transfer_type_id=None, custom_fields=None):
    """
    A user to user payment.

    :param sender: Username of the sender.
    :param receiver: Username of the receiver.
    :param amount: Transaction amount (Python ``Decimal``).
    :param description: Mandatory description of the transaction.
    :param transfer_type_id:
    :param custom_fields: List of custom field values to be associated
           with this payment
    :return: The result of the ``CyclosBackend.user_payment`` method.
    """
    # A user to user payment.
    #
    # :Params:
    #     `sender`: username of sender
    #     `receiver`: username of receiver
    #     `amount`: transaction amount
    #     `description`: description of transaction
    #
    # :Returns:
    #     a Transaction namedtuple
    #     or raises TransactionException
    return get_backend().user_payment(
        sender, receiver, amount, description, transfer_type_id,
        custom_fields)


def to_system_payment(sender, amount, description, transfer_type_id):
    """

    :Params:
        `sender`: username of sender
        `amount`: transaction amount
        `description`: description of transaction
        `transfer_type_id`: cyclos id of transaction type.

    :Returns:
        a Transaction namedtuple
        or raises TransactionException
    """
    return get_backend().to_system_payment(
        sender, amount, description, transfer_type_id)


def from_system_payment(receiver, amount, description, transfer_type_id):
    """

    :Params:
        `receiver`: username of receiver
        `amount`: transaction amount
        `description`: description of transaction
        `transfer_type_id`: cyclos id of transaction type.

    :Returns:
        a Transaction namedtuple
        or raises TransactionException
    """
    return get_backend().from_system_payment(
        receiver, amount, description, transfer_type_id)


# The following are consolidated in to one call

# def get_balance(user):
#     """ Get the current credit balance for an user. """
#     return get_backend().get_balance(user)
#
#
# def get_available_balance(user):
#     """ Get the current credit balance plus credit facility for a user. """
#     return get_backend().get_available_balance(user)
#
#
# def get_credit_limit(user):
#     """ Get credit limit for a user. """
#     return get_backend().get_credit_limit(user)


def get_account_status(username):
    """
    Get account status of user.

    :Returns:
        AccountStatus namedtuple
    """
    return get_backend().get_account_status(username)


# def get_total_count(username):
#     """
#     Get count of transactions
#
#     :Returns:
#         int
#     """
#     return get_backend().get_total_count(username)


def transactions(username=None, description=None, from_to=None, from_date=None,
                 to_date=None, direction=None, community=None,
                 account_type_id=None, currency=None):
    """ Get a list of transaction for a user or a group of users. """
    return get_backend().transactions(
        username=username,
        description=description,
        from_to=from_to,
        from_date=from_date,
        to_date=to_date,
        direction=direction,
        community=community,
        account_type_id=account_type_id,
        currency=currency)


def get_group(email):
    return get_backend().get_group(email)


def get_member_group_id():
    return get_backend().member_group_id
