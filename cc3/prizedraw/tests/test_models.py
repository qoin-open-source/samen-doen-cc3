from datetime import timedelta, date
import logging

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.translation import ugettext, ugettext_lazy as _

from cc3.cyclos.tests.test_factories import UserFactory

from ..models import (Draw, Prize, Ticket,
                      DRAW_STATUS_IN_PROGRESS, DRAW_STATUS_ENDED,
                      TicketException,
                     )

LOG = logging.getLogger(__name__)


class DrawTestCase(TestCase):

    def setUp(self):
        self.punter = UserFactory.create()
        self.admin = UserFactory.create(is_superuser=True, is_staff=True)

    def _get_in_progress_draw(self):
        now = timezone.now()
        later = now + timedelta(hours=1)
        return Draw.objects.create(draw_starts=now, draw_ends=later)

    def _get_not_started_draw(self):
        now = timezone.now()
        later = now + timedelta(hours=1)
        even_later = now + timedelta(hours=2)
        return Draw.objects.create(draw_starts=later, draw_ends=even_later)

    def _award_prize(self, prize, ticket):
        prize.winning_ticket = ticket
        prize.save()

    def _pay_prize(self, prize):
        prize.paid_by = self.admin
        prize.date_paid = date.today()
        prize.amount_paid = 10
        prize.save()

    def _get_ended_draw(self):
        now = timezone.now()
        earlier = now - timedelta(hours=1)
        even_earlier = now - timedelta(hours=2)
        return Draw.objects.create(draw_starts=even_earlier, draw_ends=earlier)

    def test_create(self):
        d = self._get_in_progress_draw()
        self.assertEqual(d.status, DRAW_STATUS_IN_PROGRESS)

    def test_draw_cant_start_after_end(self):
        now = timezone.now()
        earlier = now - timedelta(hours=1)
        self.assertRaisesMessage(
            ValidationError,
            _(u'Draw end must be after the start'),
            Draw.objects.create,
            draw_starts=now, draw_ends=earlier)

    def test_draw_number_before_started(self):
        d = self._get_not_started_draw()
        self.assertEqual(d.draw_number, '--')

    def test_draw_number_when_started(self):
        d = self._get_in_progress_draw()
        self.assertEqual(d.draw_number, '01')

    def test_cant_change_end_date_when_started(self):
        d = self._get_in_progress_draw()
        even_later = timezone.now() + timedelta(hours=2)
        d.draw_ends = even_later
        self.assertRaisesMessage(
            ValidationError,
            _(u'Draw may not be updated once start time is reached'),
            d.save)

    def test_active_days(self):
        now = timezone.now()
        later = now + timedelta(days=10, hours=1)
        d = Draw.objects.create(draw_starts=now, draw_ends=later)
        self.assertEqual(d.active_days(), 10)

    def test_get_ticket(self):
        d = self._get_in_progress_draw()
        t = d.get_new_ticket(user=self.punter, transfer_id=999)
        self.assertEqual(t.serial_number, 0)

    def test_cant_get_ticket_before_start(self):
        d = self._get_not_started_draw()
        self.assertRaisesMessage(
            TicketException,
            _(u'Tickets are not on currently sale for this draw'),
            d.get_new_ticket,
            user=self.punter, transfer_id=999)

    def test_cant_get_ticket_after_end(self):
        d = self._get_ended_draw()
        self.assertRaisesMessage(
            TicketException,
            _(u'Tickets are not on currently sale for this draw'),
            d.get_new_ticket,
            user=self.punter, transfer_id=999)

    def test_tickets_sold(self):
        d = self._get_in_progress_draw()
        t = d.get_new_ticket(user=self.punter, transfer_id=999)
        t = d.get_new_ticket(user=self.punter, transfer_id=998)
        t = d.get_new_ticket(user=self.punter, transfer_id=997)
        self.assertEqual(d.tickets_sold, 3)

    def test_get_draw_info(self):
        d = self._get_in_progress_draw()
        p = Prize.objects.create(draw=d, name='Test', absolute_amount=100)
        t = d.get_new_ticket(user=self.punter, transfer_id=999)
        t = d.get_new_ticket(user=self.punter, transfer_id=998)
        t = d.get_new_ticket(user=self.punter, transfer_id=997)
        info = d.get_draw_info()
        self.assertEqual(info['num_tickets'], 3)
        self.assertEqual(info['num_prizes'], 1)
        self.assertEqual(info['min_ticket'], 0)
        self.assertEqual(info['max_ticket'], 2)

    def test_max_tickets_user_can_buy(self):
        d = self._get_in_progress_draw()
        t = d.get_new_ticket(user=self.punter, transfer_id=999)
        t = d.get_new_ticket(user=self.punter, transfer_id=998)
        t = d.get_new_ticket(user=self.punter, transfer_id=997)
        self.assertEqual(d.max_tickets_user_can_buy(self.punter), 7)

    def test_prizes_awarded_true(self):
        d = self._get_in_progress_draw()
        p = Prize.objects.create(draw=d, name='Test', absolute_amount=100)
        t = d.get_new_ticket(user=self.punter, transfer_id=999)
        self._award_prize(p, t)
        self.assertTrue(d.prizes_awarded)

    def test_prizes_awarded_no_prizes(self):
        d = self._get_in_progress_draw()
        self.assertFalse(d.prizes_awarded)

    def test_prizes_awarded_not_all_awarded(self):
        d = self._get_in_progress_draw()
        p1 = Prize.objects.create(draw=d, name='Test1', absolute_amount=100)
        p2 = Prize.objects.create(draw=d, name='Test2', absolute_amount=100)
        t = d.get_new_ticket(user=self.punter, transfer_id=999)
        self._award_prize(p1, t)
        self.assertFalse(d.prizes_awarded)

    def test_prizes_paid_true(self):
        d = self._get_in_progress_draw()
        p = Prize.objects.create(draw=d, name='Test', absolute_amount=100)
        t = d.get_new_ticket(user=self.punter, transfer_id=999)
        self._award_prize(p, t)
        self._pay_prize(p)
        self.assertTrue(d.prizes_paid)

    def test_prizes_paid_no_prizes(self):
        d = self._get_in_progress_draw()
        self.assertFalse(d.prizes_paid)

    def test_prizes_paid_not_all_paid(self):
        d = self._get_in_progress_draw()
        p1 = Prize.objects.create(draw=d, name='Test1', absolute_amount=100)
        p2 = Prize.objects.create(draw=d, name='Test2', absolute_amount=100)
        t1 = d.get_new_ticket(user=self.punter, transfer_id=999)
        t2 = d.get_new_ticket(user=self.punter, transfer_id=998)
        self._award_prize(p1, t1)
        self._award_prize(p2, t2)
        self._pay_prize(p1)
        self.assertFalse(d.prizes_paid)


class PrizeTestCase(TestCase):

    def setUp(self):
        self.punter = UserFactory.create()
        self.admin = UserFactory.create(is_superuser=True, is_staff=True)
        now = timezone.now()
        later = now + timedelta(hours=1)
        self.draw = Draw.objects.create(draw_starts=now, draw_ends=later)

    def test_create_absolute(self):
        p = Prize.objects.create(draw=self.draw, name="Test", absolute_amount=10)
        self.assertEqual(p.amount_to_pay, 10)

    def test_create_percentage(self):
        p = Prize.objects.create(draw=self.draw, name="Test", percentage_of_take=10)
        self.assertEqual(p.amount_to_pay, 0)

    def test_create_no_amount(self):
        self.assertRaisesMessage(
            ValidationError,
            _(u'One of Absolute amount and Percentage of take must be set'),
            Prize.objects.create,
            draw=self.draw, name="Test")

    def test_create_both_amounts(self):
        self.assertRaisesMessage(
            ValidationError,
            _(u'Absolute amount and Percentage of take cannot both be set'),
            Prize.objects.create,
            draw=self.draw, name="Test", absolute_amount=10, percentage_of_take=10)

    def test_amount_to_pay_percentage(self):
        p = Prize.objects.create(draw=self.draw, name="Test", percentage_of_take=50)
        # create ten tickets, 'take'=10
        self.draw.tickets.all().delete()
        for i in range(0,10):
            self.draw.get_new_ticket(user=self.punter, transfer_id=i)
        self.assertEqual(p.amount_to_pay, 5)

    def test_amount_to_pay_percentage_non_integer(self):
        p = Prize.objects.create(draw=self.draw, name="Test", percentage_of_take=50)
        # create nine tickets, 'take'=9
        self.draw.tickets.all().delete()
        for i in range(0,9):
            self.draw.get_new_ticket(user=self.punter, transfer_id=i)
        self.assertEqual(p.amount_to_pay, 4.5)


