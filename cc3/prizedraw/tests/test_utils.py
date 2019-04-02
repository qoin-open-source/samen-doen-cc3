import logging

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.translation import ugettext, ugettext_lazy as _

from cc3.cyclos.tests.test_factories import UserFactory

from ..models import Draw, Prize, Ticket
from ..utils import (check_user_can_buy_tickets, choose_numbers,
            get_current_draw, get_previous_draw, get_total_winnings,
            get_user_winnings, get_user_win_in_last_draw)

LOG = logging.getLogger(__name__)


class UtilsTestCase(TestCase):

    def setUp(self):
        self.punter = UserFactory.create()
        self.admin = UserFactory.create(is_superuser=True, is_staff=True)

    def test_choose_numbers(self):
        numbers = choose_numbers(n=3, _min=1, _max=10)
        self.assertEqual(len(numbers), 3)

    @override_settings(RANDOMDOTORG_API_KEY="TEST_INVALID")
    def test_choose_numbers_randomdororg_fail(self):
        self.assertRaises(Exception,
                          choose_numbers,
                          n=3, _min=1, _max=10)


# TODO: MORE TESTS!
