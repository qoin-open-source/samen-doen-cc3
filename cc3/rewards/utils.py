import logging

from django.conf import settings
from django.core.mail import mail_admins
from django.utils.translation import ugettext as _

from cc3.core.models import Transaction
from cc3.core.utils.files import uploaded_file_to_filename
from cc3.cyclos import backends
from cc3.cyclos.common import TransactionException
from cc3.cyclos.models import User
from cc3.files.utils import read_csv

from .common import (UPLOAD_CSV_DELIMITERS, UPLOAD_UID_CARD,
                     UPLOAD_UID_EMAIL, UPLOAD_UID_USER_ID)
from .transactions import cause_reward

LOG = logging.getLogger(__name__)


def get_user_from_uid(uid, uid_type):
    from cc3.cards.models import Card

    user = None
    if uid_type == UPLOAD_UID_EMAIL:
        try:
            user = User.objects.get(email=uid)
        except User.DoesNotExist:
            pass
    elif uid_type == UPLOAD_UID_USER_ID:
        try:
            user = User.objects.get(id=int(uid))
        except User.DoesNotExist:
            pass
    elif uid_type == UPLOAD_UID_CARD:
        try:
            card = Card.objects.get(number__number=int(uid))
            user = card.owner
        except Card.DoesNotExist:
            pass
    # TODO other uid type(s)
    return user


def pay_reward_with_cause_donation(amount, sender, payee, description,
                                   make_cause_donation=True):
    """Make the specified user payment, then (by default) make the
    appropriate good cause payment

    :param amount: Transaction amount (Python ``Decimal``).
    :param sender: auth User
    :param payee: auth User
    :param description: Mandatory description of the transaction.
    :param make_cause_donation: make percentage good cause donation
    :return: the amount paid
    """
    transaction = None
    amount_paid = 0
    try:
        transaction = backends.user_payment(
            sender.username, payee.username, amount,
            description.decode('utf-8'))
        amount_paid = amount
    except TransactionException as e:
        LOG.error(
            u'Unable to perform user payment of {1} to {2} '
            u'transaction: {0}'.format(
                e, amount, payee.username))
    else:
        try:
            # Log the payment
            Transaction.objects.create(
                amount=amount,
                sender=sender,
                receiver=payee,
                transfer_id=transaction.transfer_id,
            )
        except Exception, e:
            # Report this to ADMINS, but treat as success
            # because the payment was made
            message = u'User payment made (transfer id={0}), but '  \
                u'failed to create Transaction: {1}'.format(
                    transaction.transfer_id, e)
            LOG.error(message)

            if not settings.DEBUG:
                mail_admins(u'Failed to log payment',
                            message, fail_silently=True)

    if transaction and make_cause_donation:
        donation = cause_reward(amount, payee, transaction.transfer_id)
        # catches and logs errors if necessary
        if donation:
            try:
                # Log the payment
                Transaction.objects.create(
                    amount=donation.amount,
                    sender=donation.sender,
                    receiver=donation.recipient,
                    transfer_id=donation.transfer_id,
                )
            except Exception, e:
                # Report this to ADMINS, but treat as success
                # because the payment was made
                message = u'Good Cause donation made (transfer id={0}), but '  \
                    u'failed to create Transaction: {1}'.format(
                        donation.transfer_id, e)
                LOG.error(message)

                if not settings.DEBUG:
                    mail_admins(u'Failed to log payment',
                                message, fail_silently=True)
    return amount_paid


def process_csv(form_data, make_payments=False, sender=None):
    """
    Process the csv file. Keep counts of valid and invalid rows, etc.
    If make_payments is True, actually perform the transactions; otherwise
    just return the stats as a dict
    """
    num_rows = 0
    num_valid_rows = 0
    unique_users = {}  # dict keyed by userID
    invalid_user_rows = []  # list of row numbers
    total_amount = 0
    num_large_amounts = 0
    amount_paid = 0

    csv_filename = uploaded_file_to_filename(form_data['csv_file'])
    has_headers = form_data.get('has_headers', False)
    uid_type = form_data['uid_type']
    uid_column = form_data['uid_column']
    amount_column = form_data['amount_column']
    description_column = form_data.get('description_column', None)
    #date_column = form_data.get('date_column', None)
    threshold_amount = form_data.get('threshold_amount', None)
    fixed_donation_percentage = form_data.get('donation_percent', None)


    if has_headers:
        skip_rows = 1
        row_number_adjust = 2
    else:
        row_number_adjust = 1
        skip_rows = 0

    for i, row in enumerate(read_csv(csv_filename,
                        delimiters=UPLOAD_CSV_DELIMITERS,
                        skip_rows=skip_rows)):
        num_rows +=1

        uid = row[uid_column]
        amount = int(row[amount_column])
        if description_column is not None:
            description = row[description_column]
        else:
            description = ''
        #if date_column is not None:
        #    txn_date = row[date_column]
        #else:
        #    txn_date = ''

        payee = get_user_from_uid(uid, uid_type)
        if not payee:
            invalid_user_rows.append(i+row_number_adjust)
            continue

        # valid user, so in theory transaction can be made
        unique_users[payee.id] = 1
        total_amount += amount
        num_valid_rows += 1
        if threshold_amount is not None and (amount > threshold_amount):
            num_large_amounts += 1

        if make_payments:
            # actually make the payment, and the cause_reward percentage payment
            amount = int(amount)
            if not description:
                description = _(u"Sum earned by user, business or institution")

            transaction = None
            try:
                transaction = backends.user_payment(
                    sender, payee.username, amount, description.decode('utf-8'))
                amount_paid += amount
            except TransactionException as e:
                LOG.error(u'Unable to perform reward payment of {1} to {2} '
                          u'transaction: {0}'.format(e,
                                                     amount,
                                                     payee.username))
            else:
                try:
                    # Log the payment
                    Transaction.objects.create(
                        amount=amount,
                        sender=sender,
                        receiver=payee,
                        transfer_id=transaction.transfer_id,
                    )
                except Exception, e:
                    # Report this to ADMINS, but treat as success
                    # because the payment was made
                    message = u'Reward payment made (transfer id={0}), but '  \
                        u'failed to create Transaction: {1}'.format(
                            transaction.transfer_id, e)
                    LOG.error(message)

                    if not settings.DEBUG:
                        mail_admins(u'Failed to log payment',
                                    message, fail_silently=True)

            if fixed_donation_percentage is None:
                description = None
            else:
                description = _(u"{0}% Cause donation (chosen by {1})").format(
                    fixed_donation_percentage, sender.cc3_profile.business_name)

            if transaction:
                donation = cause_reward(
                    amount, payee, transaction.transfer_id,
                    description= description,
                    fixed_donation_percentage=fixed_donation_percentage)
                # catches and logs errors if necessary
                if donation:
                    try:
                        # Log the payment
                        Transaction.objects.create(
                            amount=donation.amount,
                            sender=donation.sender,
                            receiver=donation.recipient,
                            transfer_id=donation.transfer_id,
                        )
                    except Exception, e:
                        # Report this to ADMINS, but treat as success
                        # because the payment was made
                        message = u'Good Cause donation made (transfer '  \
                            u'id={0}), but failed to create '  \
                            u'Transaction: {1}'.format(
                            donation.transfer_id, e)
                        LOG.error(message)

                        if not settings.DEBUG:
                            mail_admins(u'Failed to log payment',
                                        message, fail_silently=True)


    summary = {
        'num_rows': num_rows,
        'num_valid_rows': num_valid_rows,
        'num_unique_users': len(unique_users.keys()),
        'total_amount': total_amount,
        'num_large_amounts': num_large_amounts,
        'invalid_uids': invalid_user_rows,
        'threshold_amount': threshold_amount,
        'amount_paid': amount_paid,
    }
    return summary
