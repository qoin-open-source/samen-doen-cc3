import logging
import random
import string

from _mysql_exceptions import OperationalError
from datetime import timedelta, date

from cc3.accounts.sql import (
    EUROS_EARNED_AND_REDEEMED_SQL, TOTAL_DONATIONS_FROM_REWARDS)
from cc3.cyclos import dbaccess
from cc3.cyclos.utils import close_cyclos_connection, get_cyclos_connection
from django import forms
from django.conf import settings
from django.core.mail import mail_admins
from django.utils.translation import ugettext_lazy as _

from cc3.cyclos import backends

LOG = logging.getLogger(__name__)


def get_non_obvious_number(number_digits=4):
    """Cyclos needs a pin that isn't sequential - or has the same jumps
    ie, 1234, 2345, 2468, 0000 """
    number = ''

    while True:
        # noinspection PyUnusedLocal
        number = ''.join(
            random.choice(string.digits) for x in range(number_digits))
        if not is_obvious(number):
            break

    return number


def is_obvious(number_string):
    """ Algorithm from cyclos code """
    diffs = {}
    for i in range(1, len(number_string)):
        current = int(number_string[i])
        previous = int(number_string[i-1])
        diff = abs(current-previous)
        diffs[diff] = True
        if len(diffs.keys()) > 1:
            break
    if len(diffs.keys()) == 1:
        return True


def has_numbers(lp, num_numbers=1):
    number_numbers = 0
    for i in range(0, len(lp)):
        if lp[i] in string.digits:
            number_numbers += 1
        if number_numbers >= num_numbers:
            return True
    return False


def months_between(start, end):
    months = []
    cursor = start

    while cursor <= end:
        month_start = date(cursor.year, cursor.month, 1)
        if month_start not in months:
            months.append(month_start)
        cursor += timedelta(weeks=1)

    return months


def check_amount(amount, username):
    """
    :param amount: amount entered into a payment form
    :param username: account username for credit check
    :return: True or raise an error
    """
    minimum_amount = getattr(settings, 'CC3_CURRENCY_MINIMUM', 0.01)

    # check integers are being used if necessary
    if getattr(settings, "CC3_CURRENCY_INTEGER_ONLY", None):
        LOG.info('minimum_amount {0}'.format(minimum_amount))

        if minimum_amount % 1 == 0 and not amount % 1 == 0:
            raise forms.ValidationError(
                _(u'Only integer amounts are allowed.'))

    # check the amount to pay is greater than the system minimum
    if amount < minimum_amount:
        raise forms.ValidationError(
            _(u'Only amounts greater or equal to {0} are allowed.').format(
                minimum_amount))

    # NB need to use availableBalance here really - as overdrafts are
    # possible.
    available_balance = backends.get_account_status(
        username).accountStatus.availableBalance

    if amount > available_balance:
        raise forms.ValidationError(
            _(u'You do not have sufficient credit to complete the '
              u'payment'))
    return amount


def run_euro_redeemed_amounts_sql(conn, username):
    """Get
    """
    select_sql = EUROS_EARNED_AND_REDEEMED_SQL

    args = [username, ]

    for trans in dbaccess.cyclos_query_results(conn, select_sql, args):
        yield trans


def get_euros_earned_and_redeemed(username):
    conn = earned = redeemed = donated = None
    try:
        conn = get_cyclos_connection()

        for trans in run_euro_redeemed_amounts_sql(conn, username):
            earned = trans['total_saved_e']
            redeemed = trans['total_spent_e']
            donated = trans['total_donated_e']

    except OperationalError, e:
        LOG.error(e)
        mail_admins(
           "SamenDoen Get euros earned and redeemed",
           "Failed to connect to Cyclos DB"
        )
    except Exception, e:
        LOG.error(e)

    if conn:
        close_cyclos_connection(conn)

    return {
        'earned': earned,
        'redeemed': redeemed,
        'donated': donated,
    }


def total_donations_originated_by_user(username):
    conn = None
    donation = 0
    try:
        conn = get_cyclos_connection()

        select_sql = TOTAL_DONATIONS_FROM_REWARDS
        args = [username, ]

        results = dbaccess.cyclos_query_results(conn, select_sql, args)
        result = results.next()   # single row
        donation = result['donation']

    except OperationalError, e:
        LOG.error(e)
        mail_admins(
           "SamenDoen Get total donations from rewards",
           "Failed to connect to Cyclos DB"
        )
    except Exception, e:
        LOG.error(e)

    if conn:
        close_cyclos_connection(conn)

    return donation or 0
