import logging

from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models, IntegrityError
from django.db.models import Max, Min
from django.utils import timezone
from django.utils.translation import ugettext, ugettext_lazy as _, get_language
from cc3.core.utils import get_currency_symbol

LOG = logging.getLogger(__name__)


class TicketException(Exception):
    pass


DRAW_STATUS_NOT_STARTED = ugettext('Not yet started')
DRAW_STATUS_IN_PROGRESS = ugettext('In progress')
DRAW_STATUS_ENDED = ugettext('Ended, winners not yet chosen')
DRAW_STATUS_PAYMENT_PENDING = ugettext('Ended, winners not yet paid')
DRAW_STATUS_COMPLETE = ugettext('Ended, winners paid')

MAX_TICKETS_PER_DRAW = 1000000
MAX_DRAW_NUMBER = 99


class Draw(models.Model):
    """
    A prize draw

    Tickets are on sale from draw_starts up to and including draw_ends.

    Once draw_starts has been reached, the start and end dates (and
    hence the draw prefix) cannot be changed.

    After draw_ends has passed, the prizes may be awarded. This is done
    via the admin site.

    Each Draw has a unique 'prefix' used for its Ticket numbers,
    generated as {yyyy}{dd}, where yyyy is the year of draw_ends and
    {dd} is the 'draw number'. If the draw has not yet started this is '--'.
    Once the draw has started, and the end_date is fixed, the draw number
    is a unique integer for yyyy, starting from 1 and incrementing.
    """
    draw_starts = models.DateTimeField(help_text=_(
        u"Tickets go on sale from this date/time"))
    draw_ends = models.DateTimeField(help_text=_(
        u"Tickets are on sale up to this date/time"))
    max_tickets = models.PositiveIntegerField(
        default=MAX_TICKETS_PER_DRAW,
        validators=[MaxValueValidator(MAX_TICKETS_PER_DRAW)])
    max_tickets_per_person = models.PositiveIntegerField(default=10)
    ticket_price = models.PositiveIntegerField(default=1)
    _draw_number = models.IntegerField(
        default=0,
        validators=[MaxValueValidator(MAX_DRAW_NUMBER)])

    class Meta:
        ordering = ('-draw_ends',)

    def __unicode__(self):
        # TODO return self.draw_ends
        return self.prefix

    def clean(self):
        # draw_ends must not be before draw_starts
        if (self.draw_ends and self.draw_starts) and \
                (self.draw_ends < self.draw_starts):
            raise ValidationError(_(u'Draw end must be after the start'))
        # Draw may not be changed after draw_starts
        if self.pk:
            old_draw_starts = Draw.objects.get(pk=self.pk).draw_starts
            old_draw_ends = Draw.objects.get(pk=self.pk).draw_ends
            if old_draw_starts <= timezone.now():
                if ((old_draw_starts != self.draw_starts.replace(
                        microsecond=0
                )) or (old_draw_ends != self.draw_ends.replace(microsecond=0))):
                    raise ValidationError(_(
                        u'Draw may not be updated once start time is reached'))

    def save(self, **kwargs):
        """Ensure the validation happens for all creates/updates"""
        self.clean()
        return super(Draw, self).save(**kwargs)

    @property
    def prefix(self):
        """Unique prefix to identify draw e.g. for ticket number

        Concatenate {yyyy}{ddd}, eg: 2015001 where ddd is incrementing integer
        starting at 01
        """
        return "{0}{1}".format(self.draw_ends.year, self.draw_number)

    @property
    def draw_number(self):
        """Draw number for that year

        Until draw has started, this is unset ('--').
        Once it's started it can be auto-generated as the next
        integer for that year, starting at 1
        """
        if not self._draw_number:
            if self.status == DRAW_STATUS_NOT_STARTED:
                return '--'

            # need to set the field
            this_years_draws = Draw.objects.filter(
                draw_ends__year=self.draw_ends.year)
            if this_years_draws.count():
                draw_number = max(
                    [d._draw_number for d in this_years_draws.all()]) + 1
            else:
                draw_number = 1
            self._draw_number = draw_number
            self.save()

        return "{0:02}".format(self._draw_number)

    @property
    def status(self):
        """Status of the Draw"""
        now = timezone.now()
        if now < self.draw_starts:
            return DRAW_STATUS_NOT_STARTED
        if now <= self.draw_ends:
            return DRAW_STATUS_IN_PROGRESS
        # draw has ended; what state are the prizes in?
        if self.prizes_paid:
            return DRAW_STATUS_COMPLETE
        if self.prizes_awarded:
            return DRAW_STATUS_PAYMENT_PENDING
        return DRAW_STATUS_ENDED

    @property
    def tickets_sold(self):
        return self.tickets.count()

    @property
    def prizes_awarded(self):
        """Have all the prizes for this draw been awarded?

        True only if (a) prizes exist, and (b) all have winners
        """
        if self.prizes.count():
            for prize in self.prizes.all():
                if not prize.winning_ticket:
                    return False
            return True
        return False

    @property
    def prizes_paid(self):
        """Have all the prizes for this draw been marked as paid?

        True only if (a) prizes exist, and (b) all date_paid
        """
        if self.prizes.count():
            for prize in self.prizes.all():
                if not prize.date_paid:
                    return False
            return True
        return False

    @property
    def can_award_prizes(self):
        return self.status == DRAW_STATUS_ENDED

    @property
    def can_pay_prizes(self):
        return self.status == DRAW_STATUS_COMPLETE

    def get_draw_info(self):
        """Returns info needed to draw the winning numbers

        i.e. number of prizes, min and max ticket numbers
        """
        max_min = self.tickets.aggregate(
            Max('serial_number'), Min('serial_number'))
        return {
            'num_prizes': self.prizes.count(),
            'num_tickets': self.tickets.count(),
            'min_ticket': max_min['serial_number__min'],
            'max_ticket': max_min['serial_number__max'],
        }

    def max_tickets_user_can_buy(self, user):
        existing_tickets = self.tickets.filter(purchased_by=user).count()
        return self.max_tickets_per_person - existing_tickets

    def get_next_ticket_number(self):
        try:
            return self.tickets.order_by(
                '-serial_number')[0].serial_number + 1
        except IndexError:
            return 0

    def get_new_ticket(self, user, transfer_id, when_purchased=None,
                       bulk_purchase_override=False):
        """Create new ticket and assign to user

        when_purchased defaults to 'now'

        Raises TicketException if unable to create ticket
        """
        if not self.status == DRAW_STATUS_IN_PROGRESS:
            msg = ugettext(
                u"Tickets are not on currently sale for this draw")
            raise TicketException(msg)

        if bulk_purchase_override:
            # do not validate max number of tickets per person for bulk
            # 2433 Django Admin: override ticket limit for businesses
            pass
        else:
            if (self.tickets.filter(
                    purchased_by=user).count() >= self.max_tickets_per_person):
                msg = ugettext(u"You have already bought the maximum allowed "
                               u"number of tickets")
                raise TicketException(msg)
        if not when_purchased:
            when_purchased = timezone.now()
        while True:
            serial_number = self.get_next_ticket_number()
            if serial_number >= MAX_TICKETS_PER_DRAW:
                msg = ugettext(u"No more tickets are available for this draw")
                raise TicketException(msg)
            try:
                ticket = Ticket.objects.create(
                    draw=self,
                    serial_number=serial_number,
                    purchased_by=user,
                    purchase_transfer_id=transfer_id,
                    when_purchased=when_purchased)
                LOG.info(u"Assigned prize draw ticket {0} to user {1}".format(
                         ticket, user))
                return ticket
            except IntegrityError:
                continue

    def active_days(self):
        """ Return the number of days remaining before the draw """
        now = timezone.now()
        days = (self.draw_ends - now).days

        return days


class Ticket(models.Model):
    """
    Ticket in a Draw

    Ticket serial numbers are integers, unique for each Draw.
    For a given Draw, serial numbers must start at 0 and increase
    monotonically and without gaps.

    """
    draw = models.ForeignKey(Draw, related_name='tickets',
                             verbose_name=_('draw'))
    serial_number = models.PositiveIntegerField(validators=[
        MaxValueValidator(MAX_TICKETS_PER_DRAW - 1)])
    purchased_by = models.ForeignKey(
        'cyclos.User', blank=True, null=True, related_name='prizedraw_tickets')
    purchase_transfer_id = models.IntegerField(default=0)
    when_purchased = models.DateTimeField(null=True)

    class Meta:
        unique_together = ('draw', 'serial_number')

    def __unicode__(self):
        return "{0}{1:06}".format(self.draw.prefix, self.serial_number)


class Prize(models.Model):
    """
    Prize for a Draw

    There may be multiple Prizes for a draw. The prize is either an
    absolute amount (in the draw currency) or a percentage of the
    takings.
    """
    draw = models.ForeignKey(Draw, related_name='prizes',
                             verbose_name=_('draw'))
    name = models.CharField(max_length=50)  # eg: '1st prize'
    absolute_amount = models.DecimalField(
        blank=True, null=True, max_digits=8, decimal_places=2)
    percentage_of_take = models.DecimalField(
        blank=True, null=True, max_digits=5, decimal_places=2)
    winning_ticket = models.ForeignKey(
        Ticket, related_name='prizes', blank=True, null=True,
        verbose_name=_('winning_ticket'))
    date_paid = models.DateField(null=True, blank=True)
    amount_paid = models.DecimalField(
        blank=True, null=True, max_digits=8, decimal_places=2)
    paid_by = models.ForeignKey(
        'cyclos.User', blank=True, null=True, verbose_name=_("paid by"))

    class Meta:
        ordering = ('-percentage_of_take', '-absolute_amount')

    def clean(self):
        # Exactly one of absolute_amount / percentage_of_take may be set
        if self.absolute_amount and self.percentage_of_take:
            raise ValidationError(_(
                u'Absolute amount and Percentage of take cannot both be set'))
        if not (self.absolute_amount or self.percentage_of_take):
            raise ValidationError(_(
                u'One of Absolute amount and Percentage of take must be set'))

    def save(self, **kwargs):
        """Ensure the validation happens for all creates/updates"""
        self.clean()
        return super(Prize, self).save(**kwargs)

    def __unicode__(self):
        return u"{0} {1}".format(self.draw, self.name)

    @property
    def amount_summary(self):
        if self.absolute_amount:
            return u"{0} {1}".format(self.absolute_amount,
                                     get_currency_symbol())
        else:
            return _(u"{0}% of take").format(self.percentage_of_take)

    @property
    def amount_paid_summary(self):
        if self.amount_paid:
            return u"{0:.2f} {1}".format(
                self.amount_paid, get_currency_symbol())
        else:
            return u"{0:.2f} {1} ({2})".format(
                self.amount_to_pay, get_currency_symbol(),
                _(u"payment pending"))

    @property
    def amount_to_pay(self):
        """Amount that will be paid to the winner

        Calculates the percentage of take if necessary
        """
        if self.absolute_amount:
            return self.absolute_amount
        if self.percentage_of_take:
            total_take = self.draw.tickets.count() * self.draw.ticket_price
            return float(self.percentage_of_take * total_take) / 100.0
        # don't expect to get here, but
        return 0

    @property
    def payment_summary(self):
        if self.date_paid and self.paid_by:
            return ugettext(u"Paid {0} by {1}: {2}".format(
                self.date_paid, self.paid_by.username, self.amount_paid))
        if self.date_paid and not self.paid_by:
            return ugettext(u"Paid {0}: {1}".format(
                self.date_paid, self.amount_paid))
        return ""

    @property
    def winner(self):
        if self.winning_ticket:
            return "{0} ({1})".format(
                self.winning_ticket, self.winning_ticket.purchased_by)
        return ""


class RepeatPurchase(models.Model):
    """ Store information about recurring purchases for users
    """
    num_months = models.IntegerField(
        blank=True, null=True,
        help_text="Leave blank for an 'indefinite' purchase"
    )
    num_tickets = models.IntegerField(
        help_text="Number of tickets to (try and) purchase per repeat"
    )
    purchased_by = models.ForeignKey(
        'cyclos.User', blank=True, null=True,
        related_name='prizedraw_repeat_purchases')
    when_purchased = models.DateTimeField(null=True)
    end_date = models.DateTimeField(
        null=True, blank=True, help_text=(
            _(u"Auto calculated end date, used to make cronjob more efficient")
        ), editable=False)
    cancelled_date = models.DateTimeField(
        null=True, blank=True, help_text=(_(u"Date when user cancelled their "
                                            u"repeat purchase")))

    @property
    def end_month(self):
        if self.num_months:
            return self.end_date.strftime('%B %Y')
        else:
            return 'n/a'

    @property
    def purchase_type(self):
        if self.num_months:
            return _(u"Monthly")
        else:
            return _(u"Indefinite")

    @property
    def purchases_left(self):
        if self.num_months:
            total_tickets = self.num_months * self.num_tickets
            so_far = RepeatPurchaseTicket.objects.filter(
                recurring_purchase=self
            ).count()
            return total_tickets - so_far
        else:
            return 'n/a'

    @property
    def purchases_to_date(self):
        return self.repeat_purchase_tickets.count() or ''

    @property
    def cancelled(self):
        if self.cancelled_date:
            return _(u'Cancelled')

        return ''

    def __unicode__(self):
        if self.num_months:
            return u"Repeat purchase of {0} tickets for {1} ({2} - {3} " \
                   u"months)".format(self.num_tickets, self.purchased_by,
                                     self.when_purchased, self.num_months)
        else:
            return u"Repeat purchase of {0} tickets for {1} ({2} - " \
                   u"indefinite)".format(self.num_tickets, self.purchased_by,
                                         self.when_purchased)

    def save(self, *args, **kwargs):
        """
        Overrides base class ``save()`` method to update end_date when saving.

        Removes end date if num_months is blank (indefinite)
        Updates end date if num_months changes
        """
        if self.num_months:
            from dateutil.relativedelta import relativedelta
            import datetime

            self.end_date = self.when_purchased + relativedelta(
                months=self.num_months + 1)
            # set to first of month after end month
            self.end_date = timezone.make_aware(
                datetime.datetime(
                    self.end_date.year, self.end_date.month, 1),
                timezone=timezone.now().tzinfo)
        else:
            self.end_date = None

        super(RepeatPurchase, self).save(*args, **kwargs)


class RepeatPurchaseTicket(models.Model):
    """ Store tickets purchased for a particular recurring purchase
        Useful for auditing purposes - ie if
    """
    ticket = models.ForeignKey(Ticket)
    recurring_purchase = models.ForeignKey(
        RepeatPurchase, related_name='repeat_purchase_tickets')

    def __unicode__(self):
        return u"Ticket {0}, from: {1}". \
            format(self.ticket, self.recurring_purchase)


class BulkPurchase(models.Model):
    from .utils import get_current_draw

    num_tickets = models.PositiveIntegerField(
        help_text="Number of tickets to purchase in bulk"
    )
    purchased_by = models.ForeignKey(
        'cyclos.User', related_name='prizedraw_bulk_purchases')
    when_purchased = models.DateTimeField(auto_now_add=True)
    draw = models.ForeignKey(Draw, editable=False, default=get_current_draw,
                             help_text=_(u"Tickets purchased in which draw? "
                                         u"(must be current)"))

    def __unicode__(self):
        return u"{0} tickets for {1} in draw {2}".format(self.num_tickets,
                                                         self.purchased_by,
                                                         self.draw)

    def save(self, *args, **kwargs):
        from .utils import buy_tickets
        from cc3.mail.models import MailMessage, MAIL_TYPE_BULK_TICKET_PURCHASE

        super(BulkPurchase, self).save(*args, **kwargs)

        # buy the tickets
        purchaser = self.purchased_by
        data = {
            'num_tickets': self.num_tickets,
            'amount': self.num_tickets * self.draw.ticket_price
        }

        tickets_purchased = buy_tickets(data, purchaser, self.draw,
                                        bulk_purchase_override=True)

        if tickets_purchased:

            # record the purchases
            for ticket in tickets_purchased:
                bulk_ticket_purchase = BulkPurchaseTicket.objects.create(
                    bulk_purchase=self,
                    ticket=ticket
                )
                bulk_ticket_purchase.save()

            # notify the business
            try:
                self.businesses_msg = MailMessage.objects.get_msg(
                    MAIL_TYPE_BULK_TICKET_PURCHASE, lang=get_language())
            except MailMessage.DoesNotExist:
                self.businesses_msg = None
            if self.businesses_msg:
                description = ', '.join([u"{0}".format(ticket)
                                         for ticket in tickets_purchased])
                context = {'sender': purchaser,
                           'tickets_purchased': description}
                try:
                    self.businesses_msg.send(purchaser.email, context)
                except Exception as e:
                    LOG.error('Failed to send bulk purchase email to {0}: {1}'.
                              format(purchaser.email, e))
        else:
            LOG.error('Failed to bulk purchase tickets')
            raise Exception('Bulk purchased saved, but tickets not purchased. '
                            'Is the cyclos transaction id right?')


class BulkPurchaseTicket(models.Model):
    """ Store tickets purchased for a particular bulk purchase
        Useful for auditing purposes
    """
    ticket = models.ForeignKey(Ticket)
    bulk_purchase = models.ForeignKey(
        BulkPurchase, related_name='bulk_purchase_tickets')

    def __unicode__(self):
        return u"Ticket {0}, from: {1}". \
            format(self.ticket, self.bulk_purchase)
