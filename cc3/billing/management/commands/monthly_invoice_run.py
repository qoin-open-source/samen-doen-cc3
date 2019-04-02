import argparse
import datetime
import logging
import sys

from django.core.management.base import BaseCommand

from cc3.billing.utils import generate_monthly_invoices

LOG = logging.getLogger('management_commands')


class Command(BaseCommand):

    """Monthly invoicing -- create invoices and send to Twinfield"""

    leave_locale_alone = True

    help = 'Create monthly invoices and send the CSV files to Twinfield'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('monthyear', nargs=1)

    def handle(self, *args, **options):
        try:
            today = datetime.date.today()
            msg = "monthyear should be 'mm/yyyy'"
            monthyear = options['monthyear'][0]
            try:
                month, year = monthyear.split('/')
            except ValueError:
                raise argparse.ArgumentTypeError(msg)
            if not (len(year) == 4) and (len(month) == 2):
                raise argparse.ArgumentTypeError(msg)

            try:
                month = int(month)
                year = int(year)
            except ValueError:
                raise argparse.ArgumentTypeError(msg)

            generate_monthly_invoices(int(year), int(month), invoice_date=today)
        except Exception as e:
            LOG.error("!! Monthly invoicing failed: Database has "
                      "been rolled back so it can be safely re-tried once the "
                      "problem has been fixed", exc_info=sys.exc_info())
            raise e
