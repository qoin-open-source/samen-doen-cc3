import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from cc3.prizedraw.models import RepeatPurchase, RepeatPurchaseTicket
from cc3.prizedraw.utils import (buy_tickets, get_current_draw)

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    """ Auto create activation invoices. """

    help = 'Automatically purchase prize draw tickets for all current ' \
           'repeat purchase entries.'

    def handle(self, *args, **options):

        draw = get_current_draw()
        now = timezone.now()

        # for all uncancelled repeat purchases
        for repeat_purchase in RepeatPurchase.objects.filter(
            models.Q(cancelled_date__isnull=True,
                     end_date__gte=now) |
            models.Q(cancelled_date__isnull=True,
                     end_date__isnull=True)):
            try:

                purchaser = repeat_purchase.purchased_by
                total_num_tickets_this_draw = draw.tickets.filter(
                    purchased_by=purchaser).count()
                max_tickets_in_draw = draw.max_tickets_per_person

                # maximum a purchaser can buy is max per person in the draw,
                # less tickets already bought
                max_tickets_for_purchaser_in_draw = max_tickets_in_draw - \
                    total_num_tickets_this_draw

                # check how many tickets the repeat purchase already has
                # for this draw
                repeat_tickets_already_in_draw = \
                    RepeatPurchaseTicket.objects.filter(
                        recurring_purchase=repeat_purchase,
                        ticket__draw=draw).count()

                num_repeat_tickets_to_buy = repeat_purchase.num_tickets - \
                    repeat_tickets_already_in_draw

                # number of tickets has to be in the
                # range 0, max_tickets_for_purchaser_in_draw
                num_tickets = max(0, min(num_repeat_tickets_to_buy,
                                         max_tickets_for_purchaser_in_draw))

                data = {
                    'num_tickets': num_tickets,
                    'amount': draw.ticket_price * num_tickets
                }

                if num_tickets:
                    tickets_purchased = buy_tickets(data, purchaser, draw)

                    # record the purchases
                    for ticket in tickets_purchased:
                        repeat_ticket_purchase = \
                            RepeatPurchaseTicket.objects.create(
                                recurring_purchase=repeat_purchase,
                                ticket=ticket
                            )
                        repeat_ticket_purchase.save()

            except Exception, e:
                logger.error(u"Repeat Purchase failed {0}".format(e))
