from datetime import datetime, timedelta
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation

from cc3.cyclos.models import CC3Profile

LOG = logging.getLogger('cc3.accounts.check_category_matches')


class Command(BaseCommand):
    """ Check Cyclos account balances """

    help = 'Send emails about recently added Wants and Offers matching profile'

    def handle(self, *args, **options):
        LOG.info("Notify users about matching Wants/Offers")

        if not getattr(settings, 'TRACK_PROFILE_CATEGORIES', False):
            LOG.info("Wants/Offers tracking is not configured: Nothing to do")
            return

        max_age = getattr(settings, 'CATEGORY_MATCHES_EMAIL_MAX_AGE', 24)
        added_since = datetime.now() - timedelta(hours=max_age)
        LOG.info("Including Wants/Offers added since {0}".format(added_since))

        # use site language code for these emails
        translation.activate(settings.LANGUAGE_CODE)

        for profile in CC3Profile.viewable.filter(email_category_matches=True):
            LOG.debug("check_category_matches: checking {0}".format(profile))
            profile.notify_matching_categories(added_since)
