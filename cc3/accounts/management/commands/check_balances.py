import logging
import MySQLdb

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation

from cc3.cyclos.models import CC3Profile, CyclosAccount

LOG = logging.getLogger('cc3.accounts.check_balances')

CYCLOS_BALANCE_QUERY = """
SELECT DISTINCT
      m.id	AS member_id
    , IFNULL(bt.balance,0) - IFNULL(bfr.balance,0) AS balance
FROM
    accounts a 				JOIN

    members m ON
        a.member_id = m.id		LEFT JOIN

    (SELECT
       SUM(amount) AS balance, member_id
        FROM transfers t JOIN

        accounts a ON
            t.from_account_id = a.id
        GROUP BY member_id) bfr ON
        m.id = bfr.member_id	LEFT JOIN

    (SELECT
       SUM(amount) AS balance, member_id
        FROM transfers t JOIN

        accounts a ON
            t.to_account_id = a.id
        GROUP BY member_id) bt ON
        m.id = bt.member_id
WHERE
    m.id IN (%s);
"""


class Command(BaseCommand):
    """ Check Cyclos account balances """

    help = 'Perform checks for negative and overly-large balances as ' \
           'dictated by settings'

    def handle(self, *args, **options):
        LOG.info("Check Cyclos account balances")
        track_negative_balances = getattr(
            settings, 'TRACK_NEGATIVE_BALANCES', False)
        large_balance_limit = getattr(
            settings, 'TRACK_LARGE_BALANCE_LIMIT', None)
        track_large_balances = large_balance_limit is not None

        if track_negative_balances:
            LOG.info("Tracking negative balances")
        if track_large_balances:
            LOG.info("Tracking large balances, limit={0}".format(
                large_balance_limit))
        if not track_negative_balances and not track_large_balances:
            LOG.info("Balance tracking is not configured: Nothing to do")
            return

        # use site language code for emails
        translation.activate(settings.LANGUAGE_CODE)

        cyclos_accounts = CyclosAccount.objects.filter(
            cc3_profile__is_approved=True)
        # TODO: check this is the right subset
        LOG.info("Found {0} accounts to check".format(cyclos_accounts.count()))

        id_list = ', '.join(
            [str(account.cyclos_id) for account in cyclos_accounts.all()])
        cyclos_sql = CYCLOS_BALANCE_QUERY % id_list
        args = ()

        conn = get_cyclos_connection()

        LOG.info("Fetching latest balance for these accounts")
        balances_checked = 0
        for cyclos_account_id, balance in \
                cyclos_query_results(conn, cyclos_sql, args):
            cyclos_account = CyclosAccount.objects.get(pk=cyclos_account_id)
            LOG.debug(u"Checking {0}; current balance={1}".format(
                cyclos_account.cc3_profile, balance))

            # Track large balances (incl. sending email if needed)
            if track_large_balances:
                cyclos_account.cc3_profile.track_large_balance(balance)

            # Track negative balances
            if track_negative_balances:
                cyclos_account.cc3_profile.track_negative_balance(balance)

            balances_checked += 1

        close_cyclos_connection(conn)
        LOG.info("Retrieved and checked {0} balances".format(balances_checked))

        # Now send any negative-balance notification emails that are due today
        if track_negative_balances:
            LOG.info("Sending any negative balance warning emails")
            for profile in CC3Profile.objects.filter(
                    negative_balance_start_date__isnull=False,
                    negative_balance_warning_sent__isnull=True).all():
                if profile.negative_balance_warning_due():
                    profile.send_negative_balance_warning_emails()

            LOG.info("Sending any negative balance collection emails")
            for profile in CC3Profile.objects.filter(
                    negative_balance_start_date__isnull=False,
                    negative_balance_collect_sent__isnull=True).all():
                if profile.negative_balance_collect_due():
                    profile.send_negative_balance_collect_emails()


# These values work for the Vagrant setup
CYCLOS_DB_CONFIG = {
    'user': getattr(settings, "CYCLOS_DB_USER", 'cyclos3'),
    'passwd': getattr(settings, "CYCLOS_DB_PASSWD", 'cyclos3'),
    'host': getattr(settings, "CYCLOS_DB_HOST", '192.168.100.2'),
    'db': getattr(settings, "CYCLOS_DB", 'cyclos3'),
}

ROWLIMIT = 1000


def get_cyclos_connection():
    db = MySQLdb.connect(**CYCLOS_DB_CONFIG)
    return {
        'db': db,
        'cursor': db.cursor()
    }


def close_cyclos_connection(connection):
    connection['cursor'].close()
    connection['db'].close()


def cyclos_query_results(connection, sql, args):
    connection['cursor'].execute(sql, args)
    while True:
        results = connection['cursor'].fetchmany(ROWLIMIT)
        LOG.debug("Fetched {0} results".format(len(results)))
        if not results:
            break
        for row in results:
            yield row
