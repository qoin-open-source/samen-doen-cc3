import datetime
import logging

from django.core.management.base import BaseCommand

from cc3.cyclos.models import CC3Profile

from cc3.invoices.utils import auto_create_invoice

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    """ Auto create monthly invoices. """

    help = 'Automatically create monthly invoices for all users in a group ' \
           'that have this enabled'

    def handle(self, *args, **options):
        today = datetime.date.today()
        for profile in CC3Profile.viewable.all():
            logger.info(u"Checking monthly invoices for user {0}".format(
                profile))
            group = profile.get_cyclos_group()
            logger.info(u"Group for user: {0}".format(group))
            if not group:
                logger.info(u"Ignoring user without Cyclos Group")
                continue
            if not group.create_monthly_invoice:
                logger.info(
                    u"Ignoring user, group has monthly invoices disabled")
                continue
            if today.day != group.invoice_day_otm:
                logger.info(
                    u"Ignoring user, not the correct day of the month ({0}) "
                    u"for monthly invoices".format(group.invoice_day_otm))
                continue
            if not group.invoice_currency or not group.invoice_user:
                logger.warning(
                    u"Not creating invoices, currency or sender not specified")
                continue

            if auto_create_invoice(
                    profile, group.invoice_currency, group.invoice_user,
                    amount=group.invoice_monthly_amount if group.invoice_monthly_amount else None,
                    invoice_type='monthly',
                    invoice_description=group.invoice_monthly_description):
                logger.info(u"Monthly invoice for user {0} created "
                            u"successfully".format(profile))
            else:
                logger.error(u"Unable to create invoice for user {0}".format(
                    profile))
