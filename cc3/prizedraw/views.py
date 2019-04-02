import datetime
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseForbidden
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (FormView, TemplateView,
                                  ListView)

from cc3.cards.views_api import load_class
from cc3.cards.nice_pass import nicepass

from .forms import BuyTicketsForm, CancelRepeatPurchaseForm, \
    ValidateUserNumTicketsForm, PrizeDrawNewUserForm
from .models import Prize, TicketException
from .utils import (get_current_draw, check_user_can_buy_tickets,
                    get_user_winnings, get_total_winnings,
                    buy_tickets, setup_repeat_purchase)

LOG = logging.getLogger(__name__)


class PrizeDrawHomeView(TemplateView):
    template_name = 'prizedraw/home.html'

    def get_context_data(self, **kwargs):
        now = timezone.now()
        context = super(PrizeDrawHomeView, self).get_context_data(**kwargs)
        context['lottery_name'] = getattr(
            settings, 'PRIZEDRAW_LOTTERY_NAME', 'Prize Draws')
        next_draw = get_current_draw()
        context['next_draw'] = next_draw
        if next_draw:
            context['max_tickets_to_buy'] = max(
                0, next_draw.max_tickets_user_can_buy(self.request.user))
            context['my_tickets'] = next_draw.tickets.filter(
                purchased_by=self.request.user)
        num_prizes, total_winnings = get_user_winnings(self.request.user)
        context['my_winnings_to_date'] = total_winnings
        context['my_prizes_to_date'] = num_prizes
        context['my_past_tickets'] =  \
            self.request.user.prizedraw_tickets.exclude(
            draw__draw_ends__gt=now).order_by(
            '-when_purchased', '-serial_number')
        num_prizes, num_winners, total_winnings = get_total_winnings()
        context['winnings_to_date'] = total_winnings
        context['prizes_to_date'] = num_prizes
        context['winners_to_date'] = num_winners
        context['past_prizes'] = Prize.objects.filter(
            winning_ticket__isnull=False).order_by('-draw__draw_ends')
        return context


class MyPastResultsView(ListView):
    template_name = 'prizedraw/my_results.html'
    paginate_by = 30

    def get_queryset(self):
        now = timezone.now()
        return self.request.user.prizedraw_tickets.exclude(
            draw__draw_ends__gt=now).order_by(
            '-when_purchased', '-serial_number')

    def get_context_data(self, **kwargs):
        context = super(MyPastResultsView, self).get_context_data(**kwargs)
        num_prizes, total_winnings = get_user_winnings(self.request.user)
        context['my_winnings_to_date'] = total_winnings
        context['my_prizes_to_date'] = num_prizes
        context['lottery_name'] = getattr(
            settings, 'PRIZEDRAW_LOTTERY_NAME', 'Prize Draws')
        return context


class BuyTicketsFormView(FormView):
    template_name = 'prizedraw/buy_tickets.html'
    success_url = reverse_lazy('prizedraw_home')
    TRANSFER_TYPE_ID = 47   # override in settings if necessary

    def dispatch(self, request, *args, **kwargs):
        """
        Get user's profile and current draw for later
        """
        self.cc3_profile = request.user.get_cc3_profile()
        self.draw = get_current_draw()
        if not self.draw:
            messages.error(self.request, _(u"There is no draw in progress"))
        return super(BuyTicketsFormView, self).dispatch(
            request, *args, **kwargs)

    def get_form(self, form_class):
        """
        Overrides the parent ``get_form`` method. Returns the 'Buy tickets'
        form, or ``None`` (no form at all) if the user is not allowed to
        buy any tickets.
        """
        if self.cc3_profile and self.cc3_profile.web_payments_enabled:
            try:
                check_user_can_buy_tickets(1, self.request.user,
                                           draw=self.draw)
            except TicketException, e:
                messages.error(self.request, e)
            else:
                kwargs = self.get_form_kwargs()
                kwargs['user'] = self.request.user
                kwargs['draw'] = self.draw
                return BuyTicketsForm(**kwargs)
            return None

        return None

    def form_valid(self, form):
        # prevent duplicate payments if using modal dialog box
        # with confirmation (and timeout for double clicks)
        if self.request.is_ajax():
            # if we're dealing with ajax, wait for 2nd submit,
            # where POST has 'confirmed key'
            if not 'confirmed' in self.request.POST:
                data = json.dumps({
                    'success': True,
                    'num_tickets': form.cleaned_data['num_tickets'],
                    'num_months': form.cleaned_data['num_months'],
                    'run_indefinitely': form.cleaned_data['run_indefinitely'],
                    'repeat_purchase': form.cleaned_data['repeat_purchase'],
                    'amount': form.cleaned_data['amount']
                })
                return HttpResponse(data, {
                    'content_type': 'application/json',
                })

        tickets_purchased = buy_tickets(form.cleaned_data,
                                        self.request.user,
                                        self.draw,
                                        self.request)
        if form.cleaned_data['repeat_purchase']:
            setup_repeat_purchase(
                form.cleaned_data, tickets_purchased, self.request.user,
                self.request)

        return super(BuyTicketsFormView, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            data = json.dumps(form.errors)
            response_kwargs = {
                'status': 400,
                'content_type': 'application/json'
            }
            return HttpResponse(data, **response_kwargs)

        return super(BuyTicketsFormView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(BuyTicketsFormView, self).get_context_data(**kwargs)
        context['draw'] = self.draw
        if self.draw:
            context['max_tickets_to_buy'] = max(
                0, self.draw.max_tickets_user_can_buy(self.request.user))
        else:
            # no draw
            context['max_tickets_to_buy'] = 0
        return context


class MyRepeatPurchasesView(ListView):
    template_name = 'prizedraw/my_repeat_purchases.html'
    paginate_by = 30

    def get_queryset(self):
        return self.request.user.prizedraw_repeat_purchases.order_by(
            '-when_purchased')

    def get_context_data(self, **kwargs):
        context = super(MyRepeatPurchasesView, self).get_context_data(**kwargs)
        context['lottery_name'] = getattr(
            settings, 'PRIZEDRAW_LOTTERY_NAME', 'Prize Draws')
        return context


class CancelRepeatPurchaseView(FormView):
    form_class = CancelRepeatPurchaseForm
    template_name = "prizedraw/cancel_repeat_purchase.html"

    def get_form(self, form_class):
        """
        Overrides the parent ``get_form`` method. Sets the user for the Form
        so that validation can happen there.
        """
        kwargs = self.get_form_kwargs()
        kwargs['user'] = self.request.user
        return form_class(**kwargs)

    def get_success_url(self):
        return reverse('prizedraw_my_repeat_purchases')

    def form_valid(self, form):
        # if using modal dialog box, validate and return response
        if self.request.is_ajax():
            if not 'confirmed' in self.request.POST:
                data = json.dumps({
                    'success': True,
                    'pk': form.cleaned_data['pk'],
                })
                return HttpResponse(data, {
                    'content_type': 'application/json',
                })

        repeat_purchase = form.instance
        repeat_purchase.cancelled_date = datetime.datetime.now()
        repeat_purchase.save()
        messages.add_message(
            self.request, messages.INFO,
            _(u"Your repeat purchase has been cancelled"))

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.is_ajax():
            data = json.dumps(form.errors)
            response_kwargs = {
                'status': 400,
                'content_type': 'application/json'
            }
            return HttpResponse(data, **response_kwargs)

        messages.add_message(
            self.request, messages.WARNING, _(u"Cannot cancel repeat purchase"))

        return HttpResponseRedirect(self.get_success_url())


def json_dumps(d):
    def fix_dict(_dict):
        fixed = {}
        for k, v in _dict.iteritems():
            if isinstance(v, Decimal):
                # convert decimal to string
                fixed.update({k: str(v)})
            elif isinstance(v, dict):
                # recurse
                fixed.update({k: fix_dict(v)})
            elif isinstance(v, datetime.datetime):
                # convert datetime to isoformat string
                fixed.update({k: v.isoformat()})
            else:
                # no conversion needed, replace
                fixed.update({k: v})
        return fixed
    return json.dumps(fix_dict(d))


def current_draw_info(request):
    """
    Return prize draw info about next draw, remaining tickets and ticket price.

    Used by Brixton Bonus ticket purchasing php page, and
    Brixton Bonus background ticket processing php page (for price)
    :param request:
    :return: JSON dictionary containing
     - ticket_price
     - prizedraw_starts
     - prizedraw_end
     - prizedraw_open

     ie:

     {"prizedraw_ends": null, "prizedraw_starts": null,
      "ticket_price": "1", "prizedraw_open": false}
    """
    prizedraw_draw_starts = None
    prizedraw_draw_ends = None
    ticket_price = Decimal(1.0)
    max_tickets_per_person = None
    next_draw = get_current_draw()
    if next_draw:
        ticket_price = Decimal(next_draw.ticket_price)
        prizedraw_draw_ends = next_draw.draw_ends
        prizedraw_draw_starts = next_draw.draw_starts
        max_tickets_per_person = next_draw.max_tickets_per_person

    data = {
        'prizedraw_open': True if next_draw else False,
        'prizedraw_starts': prizedraw_draw_starts,
        'prizedraw_ends': prizedraw_draw_ends,
        'ticket_price': ticket_price,
        'max_tickets_per_person': max_tickets_per_person
    }

    return HttpResponse(
        json_dumps(data),
        content_type='application/json'
    )
