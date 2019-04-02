import logging

from django.core.management.base import BaseCommand

from cc3.cyclos.models import CC3Profile

from cc3.invoices.utils import auto_create_invoice

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    """ Auto create activation invoices. """

    help = '''Automatically create activation invoices for all users in a group
              that have this enabled, this happens at most once. This is
              checked daily as users can switch groups in Cyclos without Django
               knowing about it.'''

    def handle(self, *args, **options):
        for profile in CC3Profile.viewable.filter(
                has_received_activation_invoice=False):
            logger.info(u"Checking activation invoices for user {0}".format(
                profile))
            group = profile.get_cyclos_group()
            logger.info(u"Group for user: {0}".format(group))
            if not group:
                logger.info(u"Ignoring user without Cyclos Group")
                continue
            if not group.create_activation_invoice:
                logger.info(
                    u"Ignoring user, group has activation invoices disabled")
                continue
            if not group.invoice_currency or not group.invoice_user:
                logger.warning(
                    u"Not creating invoices, currency or sender not specified")
                continue

            if auto_create_invoice(
                    profile, group.invoice_currency, group.invoice_user,
                    amount=group.invoice_activation_amount if group.invoice_activation_amount else None,
                    invoice_type='activation',
                    invoice_description=group.invoice_activation_description):
                logger.info(u"Activation invoice for user {0} created "
                            u"successfully".format(profile))
                profile.has_received_activation_invoice = True
                profile.save()
            else:
                logger.error(u"Unable to create invoice for user {0}".format(
                    profile))
