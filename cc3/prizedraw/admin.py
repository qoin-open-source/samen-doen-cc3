import logging

from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib import admin, messages
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import (RequestContext, render_to_response,
                              get_object_or_404)
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html

from .models import (Draw, Prize, Ticket, RepeatPurchase, RepeatPurchaseTicket,
                     BulkPurchase, BulkPurchaseTicket)
from .forms import AwardPrizesForm
from .utils import choose_numbers

LOG = logging.getLogger(__name__)


class TicketAdmin(admin.ModelAdmin):
    list_filter = ('draw',)

    def has_add_permission(self, request):
        """Don't allow Tickets to be added via Admin

        They are only created in conjunction with a Card or online payment
        """
        return getattr(settings, "PRIZEDRAW_ADD_TICKETS_VIA_ADMIN", True)


# TODO: Add a proper 'record_payment' view and form, so we don't need to
# expose this (?)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ('draw', 'name', 'amount_summary', 'winner',
                    'payment_summary',)
    list_display_links = ('name',)
    readonly_fields = ('draw', 'winning_ticket', 'winner')

    def has_add_permission(self, request):
        """Don't allow Prizes to be added here -- must do it via Inline"""
        return False

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """Filter paid_by choices to be only admin users"""
        field = super(PrizeAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)
        if db_field.name == 'paid_by':
            field.queryset = field.queryset.filter(is_staff=True)
        return field


class PrizeInline(admin.TabularInline):
    model = Prize
    extra = 1
    readonly_fields = ('winner', 'payment_status')
    fields = ('name', 'absolute_amount', 'percentage_of_take',
              'winner', 'payment_status')

    def payment_status(self, instance):
        if not instance.winning_ticket:
            return ""
        if instance.date_paid:
            return instance.payment_summary
        url = reverse('admin:prizedraw_prize_change',
                      args=(instance.pk,))
        return format_html(u'<a href="{0}">Record payment</a>', url)


class DrawAdmin(admin.ModelAdmin):
    list_display = ('prefix', 'draw_starts', 'draw_ends', 'status',
                    'tickets_sold', 'ticket_price')
    inlines = (PrizeInline,)
    readonly_fields = ('_draw_number',)

    def award_prizes_view(self, request, pk):
        """
        Chooses a winning Ticket for each Prize in the Draw
        """
        form = None
        draw = get_object_or_404(Draw, pk=pk)
        if not draw.can_award_prizes:
            messages.error(request, _(
                "Cannot generate winning numbers for this draw "
                "- check status"))
        else:
            if request.method == 'POST':
                form = AwardPrizesForm(request.POST)
                if form.is_valid():
                    draw_info = draw.get_draw_info()
                    if draw_info['num_prizes'] > draw_info['num_tickets']:
                        messages.error(request, _("Not enough tickets to award "
                                                  "prizes"))
                    elif draw_info['num_prizes'] < 1:
                        messages.error(request, _("No prizes to award"))
                    else:
                        # Generate the random numbers ...
                        try:
                            winning_numbers = choose_numbers(
                                            n=draw_info['num_prizes'],
                                            _min=draw_info['min_ticket'],
                                            _max=draw_info['max_ticket'])
                        except Exception, e:
                            winning_numbers = None
                            messages.error(
                                request,
                                _("Unable to generate prize numbers "
                                  "-- Please try again later"))
                            # notify admins of the failure
                            admin_message = u"Attempt to generate winning "  \
                                "numbers for Draw {0} failed.\n\n" \
                                "Contacting random.org raised exception:\n"  \
                                "{1}".format(draw, e)
                            mail_admins(u'Failed to generate winning numbers for draw',
                                        admin_message, fail_silently=True)

                        if winning_numbers:
                            LOG.info("Draw {0}, winning numbers: {1}".format(
                                                        draw, winning_numbers))
                            messages.success(request,
                                _("Winning numbers generated: {0}".format(
                                                            winning_numbers)))

                            # ... and allocate to Prizes
                            for prize in draw.prizes.all():
                                winning_number = winning_numbers.pop()
                                prize.winning_ticket = draw.tickets.get(
                                    serial_number=winning_number)
                                prize.save()

                            return HttpResponseRedirect(
                                reverse('admin:prizedraw_draw_change',
                                        args=(pk,)))
            else:
                form = AwardPrizesForm()

        return render_to_response(
            'admin/prizedraw/draw/award_prizes.html',
            {'form': form,
             'title': _('Generate winning tickets for Draw {0}').format(draw),
             'draw': draw,
             },
            RequestContext(request))

    def get_urls(self):
        urls = super(DrawAdmin, self).get_urls()
        custom_urls = patterns(
            '',
            url(r'^award_prizes/(?P<pk>\d+)/$',
                self.admin_site.admin_view(self.award_prizes_view),
                name='prizedraw_draw_award_prizes'),
        )

        return custom_urls + urls


class RepeatPurchaseAdmin(admin.ModelAdmin):
    list_display = ('purchased_by', 'purchase_type', 'num_tickets',
                    'when_purchased', 'end_month', 'purchases_left',
                    'cancelled')
    list_filter = ('purchased_by', )


class RepeatPurchaseTicketAdmin(admin.ModelAdmin):
    list_filter = ('ticket__draw', 'recurring_purchase')

    def has_add_permission(self, request):
        """Don't allow Tickets to be added via Admin

        They are only created in conjunction with a Card or online payment
        """
        return False


class BulkPurchaseAdminForm(forms.ModelForm):
    model = BulkPurchase

    def clean(self):
        from .utils import get_current_draw
        from cc3.cyclos import backends
#        from cc3.cyclos.models import User

        cd = self.cleaned_data
        current_draw = get_current_draw()

        if current_draw is None:
            raise forms.ValidationError(_(u"There is no current draw, bulk "
                                          u"purchases are not available"))

        if cd['num_tickets'] <= 0:
            raise forms.ValidationError(_(u"Please enter a number greater than "
                                          u"1"))

        is_business = False
        try:
            business_cc3_profile = cd['purchased_by'].get_profile()
            is_business = business_cc3_profile.is_business_profile()
        except Exception, e:
            pass

        if not is_business:
            raise forms.ValidationError(_(u"Admin users can only make bulk "
                                          u"ticket purchases for Businesses"))

        # validate user has enough credit
        available_balance = backends.get_account_status(
            cd['purchased_by'].username).accountStatus.availableBalance
        ticket_cost = cd['num_tickets'] * current_draw.ticket_price
        if ticket_cost > available_balance:
            raise forms.ValidationError(
                _(u"You don't have enough credit"))

        # not currently validating max tickets in draw, so no point doing this:
        #        if cd['num_tickets'] > current_draw.remaining_tickets:
        #            raise forms.ValidationError(_(u"Only {0} tickets left
        # for draw".format(current_draw.remaining_tickets)))

        return cd


class BulkPurchaseAdmin(admin.ModelAdmin):
    list_display = ('purchased_by', 'num_tickets', 'when_purchased', 'draw')
    list_filter = ('draw', 'purchased_by')
    form = BulkPurchaseAdminForm


class BulkPurchaseTicketAdmin(admin.ModelAdmin):
    list_filter = ('ticket__draw', 'bulk_purchase')

    def has_add_permission(self, request):
        """Don't allow Tickets to be added via Admin

        They are only created by the bulk purchase admin screen
        """
        return False


admin.site.register(Draw, DrawAdmin)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(Prize, PrizeAdmin)
admin.site.register(RepeatPurchase, RepeatPurchaseAdmin)
admin.site.register(RepeatPurchaseTicket, RepeatPurchaseTicketAdmin)
admin.site.register(BulkPurchase, BulkPurchaseAdmin)
admin.site.register(BulkPurchaseTicket, BulkPurchaseTicketAdmin)
