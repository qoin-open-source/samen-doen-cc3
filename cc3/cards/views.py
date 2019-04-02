import datetime
import logging

from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect, HttpResponseForbidden
from django.db import models
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils import translation
from django.utils.datastructures import SortedDict
from django.utils.formats import date_format, time_format
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.generic import (FormView,
    CreateView, DeleteView, ListView, TemplateView, UpdateView)

from .forms import (OperatorForm, OwnerRegisterCardForm, BlockCardForm,
                    FulfillmentProcessForm)
from .models import (
    Operator, Terminal, Card, CardRegistration, Fulfillment,
    CARD_FULFILLMENT_STATUSES, CardTransaction)
from .utils import mail_card_admins, generate_card_fulfillment_excel

from cc3.communityadmin.views import CommunityMixin
from cc3.excelexport.views import ExcelResponse
from cc3.mail.models import MAIL_TYPE_SEND_USER_CARD

from .models import CARD_FULLFILLMENT_CHOICE_NEW, CARD_FULLFILLMENT_CHOICE_MANUALLY_PROCESSED, CARD_FULLFILLMENT_CHOICE_ACCOUNT_CLOSED


LOG = logging.getLogger(__name__)


class NFCTerminalsListView(ListView):
    model = Terminal
    context_object_name = 'terminals'
    template_name = 'cards/business_terminals.html'

    def get_queryset(self):
        return Terminal.objects.filter(business=self.request.user)

    def get_context_data(self, **kwargs):
        """
        Overrides ``get_context_data`` base method to add the ``Operator``s
        related to these terminals.
        """
        context = super(NFCTerminalsListView, self).get_context_data(**kwargs)
        context['operators'] = Operator.objects.filter(
            business=self.request.user)

        if hasattr(self.request.user, 'businesscausesettings'):
            context['reward_percentage'] = self.request.user.businesscausesettings.reward_percentage
            context['transaction_percentage'] = self.request.user.businesscausesettings.transaction_percentage

        return context

from django.core.exceptions import ValidationError

class OperatorCreateView(CreateView):
    model = Operator
    form_class = OperatorForm
    template_name = 'cards/operator_form.html'
    success_url = reverse_lazy('terminals_list')

    # #3207 Provide the initial value for the business field of the form
    def get_initial(self):
        return {'business': self.request.user}


class OperatorUpdateView(UpdateView):
    model = Operator
    form_class = OperatorForm
    template_name = 'cards/operator_form.html'
    success_url = reverse_lazy('terminals_list')

    # #3207 Provide the initial value for the business field of the form
    def get_initial(self):
        return {'business': self.request.user}


class OperatorDeleteView(DeleteView):
    model = Operator
    success_url = reverse_lazy('terminals_list')


class OwnerBlockUnblockCardView(UpdateView):
    model = Card
    form_class = BlockCardForm
    template_name = "cards/owner_block_card_form.html"
    success_url = reverse_lazy('owner_manage_and_register_cards')
    action = 'block'

    def form_valid(self, form):
        LOG.info("OwnerBlockUnblockCardView: action={1} on {0}".format(
            form.instance, self.action))
        if self.action == 'block':
            form.instance.block_card()
            messages.add_message(self.request, messages.INFO,
                                 _(u"You have blocked your card"))
        elif self.action == 'unblock':
            form.instance.unblock_card()
            messages.add_message(self.request, messages.INFO,
                                 _(u"You have re-activated your card"))
        return super(OwnerBlockUnblockCardView, self).form_valid(form)

    def get_object(self, *args, **kwargs):
        # only the owner is allowed, and then only if site is
        # configured to allow it
        if not getattr(settings, 'USERS_CAN_BLOCK_CARDS', False):
            raise PermissionDenied
        obj = super(OwnerBlockUnblockCardView, self).get_object(*args, **kwargs)
        if not obj.owner == self.request.user:
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        context = super(OwnerBlockUnblockCardView,
                        self).get_context_data(**kwargs)

        context['action'] = self.action

        return context


class CardFulfillmentListView(CommunityMixin, ListView):
    model = Fulfillment
    template_name = 'cards/fulfillment_list.html'
    paginate_by = 10
    context_object_name = 'fulfillment_list'

    def get_queryset(self):
        community = self.request.user.get_admin_community()

        fulfillment_list = Fulfillment.objects.filter(
            profile__community=community,
        )
        return fulfillment_list

    def post(self, request, *args, **kwargs):
        """ override post for excel functionality """

        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if (self.get_paginate_by(self.object_list) is not None
                    and hasattr(self.object_list, 'exists')):
                is_empty = not self.object_list.exists()
            else:
                is_empty = len(self.object_list) == 0
            if is_empty:
                raise Http404(
                    _("Empty list and '{class_name}.allow_empty' is "
                      "False.".format(class_name=self.__class__.__name__)))

        context = self.get_context_data(object_list=self.object_list)
        if 'export' in request.POST and request.POST['export'] == u'export':
            return generate_card_fulfillment_excel(self.object_list)

        if 'mark_processed' in request.POST:
            form = FulfillmentProcessForm(request.POST)
            if form.is_valid():
                fulfillment = Fulfillment.objects.get(
                    pk=form.cleaned_data['mark_processed'])
                fulfillment.status = CARD_FULFILLMENT_STATUSES[1][1]
                fulfillment.save()
                return HttpResponseRedirect(reverse_lazy('cardfulfillment'))
        return self.render_to_response(context)


def owner_register_card(
        request, template_name="cards/owner_register_card_form.html"):
    # prevent users from making a choice re card registration if they have
    # already done so?
    cc3_profile = request.user.cc3_profile
    cc3_profile_pays_for_card = cc3_profile.pays_for_card()
    if cc3_profile.can_order_card() and request.POST:
        # the restriction for the number of cards can be set here with
        # if request.user.card_registration_set.count() < 3:
        # or via the cc3_profile.can_order_card()
        form = OwnerRegisterCardForm(
            cc3_profile=cc3_profile, data=request.POST)
        if form.is_valid():
            message = None

            card_registration = CardRegistration.objects.create(
                owner=request.user,
                registration_choice=form.cleaned_data['registration_choice'])

            if form.cleaned_data['registration_choice'] == 'Old':
                message = _(u'Your request for a new card has been '
                            u'received. It will be delivered within three '
                            u'working days at the address you specified.')
            elif form.cleaned_data['registration_choice'] == 'Send':
                message = _(u'Your request for a new card has been '
                            u'received. It will be delivered within three '
                            u'working days at the address you specified.')

            if cc3_profile_pays_for_card:
                message = _(u'Your request for a new card has been '
                            u'received. It will be delivered within '
                            u'three working days at the address you '
                            u'specified. We will deduct the fee for '
                            u'this card by direct debit.')

            mail_type_choice = MAIL_TYPE_SEND_USER_CARD
            # start fulfillment process
            Fulfillment.objects.create(
                profile=cc3_profile,
                card_registration=card_registration,
                status='New'
            )
            # send an email about the card request
            mail_card_admins(cc3_profile, mail_type_choice,
                             translation.get_language())

            if message:
                messages.add_message(request, messages.INFO, message)

            return HttpResponseRedirect(
                reverse_lazy('owner_register_card_success'))
    else:
        form = OwnerRegisterCardForm(cc3_profile=cc3_profile)

    return render_to_response(template_name, {
        'form': form,
        'cc3_profile_pays_for_card': cc3_profile_pays_for_card
    }, context_instance=RequestContext(request))


class OwnerManageCardView(TemplateView):
    template_name = 'cards/owner_manage_card_form.html'

    def get_context_data(self, **kwargs):
        context = super(OwnerManageCardView, self).get_context_data(**kwargs)

        context['owners_cards'] = Card.objects.filter(
            owner=self.request.user
        ).exclude(
            expiration_date__lte=datetime.datetime.now()
        ).order_by('-creation_date')

        context['card_registrations'] = CardRegistration.objects.filter(
            owner=self.request.user
        ).order_by('-creation_date')

        return context


# Combination of the above two views (and therefore duplicates some code)
# Currently just used on Troeven.
# ... and now Samen Doen
class OwnerManageAndRegisterCardsView(FormView):
    template_name = 'cards/owner_manage_card_form.html'
    form_class = OwnerRegisterCardForm
    success_url = "."

    def dispatch(self, request, *args, **kwargs):
        # parse the request here ie.
        self.cc3_profile = self.request.user.get_profile()
        self.cc3_profile_pays_for_card = self.cc3_profile.pays_for_card()

        # call the view
        return super(OwnerManageAndRegisterCardsView,
                     self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(OwnerManageAndRegisterCardsView,
                                        self).get_form_kwargs()
        kwargs['cc3_profile'] = self.request.user.cc3_profile

        return kwargs

    def get_context_data(self, **kwargs):
        context = super(OwnerManageAndRegisterCardsView,
                                        self).get_context_data(**kwargs)

        context['owners_cards'] = Card.objects.filter(
            owner=self.request.user
        ).exclude(
            expiration_date__lte=datetime.datetime.now()
        ).order_by('-creation_date')

        # #3421 Change the model that the card requests list is based on
        # so that it gets updated automatically as community admins create new
        # cards or cancel requests
        # Only pass the fulfillments that match the logged in user and that have not already been
        # fulfilled with an activated card
        context['fulfillments'] = Fulfillment.objects.filter(profile__id=self.request.user.cc3_profile.id)\
            .exclude(status=CARD_FULLFILLMENT_CHOICE_MANUALLY_PROCESSED)\
            .order_by('-creation_date')

        # Pass the strings for the New and Cancelled statuses so that the template
        # is able to display different things depending on the value of the status attribute
        context['CARD_FULLFILLMENT_CHOICE_NEW'] = CARD_FULLFILLMENT_CHOICE_NEW
        context['CARD_FULLFILLMENT_CHOICE_ACCOUNT_CLOSED'] = CARD_FULLFILLMENT_CHOICE_ACCOUNT_CLOSED

        context['cc3_profile_pays_for_card'] = self.cc3_profile_pays_for_card

        return context

    def form_valid(self, form):
        message = None

        card_registration = CardRegistration.objects.create(
            owner=self.request.user,
            registration_choice=form.cleaned_data['registration_choice'])

        if form.cleaned_data['registration_choice'] == 'Old':
            message = _(u'Your request for a new card has been '
                        u'received. It will be delivered within three '
                        u'working days at the address you specified.')
        elif form.cleaned_data['registration_choice'] == 'Send':
            message = _(u'Your request for a new card has been '
                        u'received. It will be delivered within three '
                        u'working days at the address you specified.')
        if self.cc3_profile_pays_for_card:
            message = _(u'Your request for a new card has been '
                        u'received. It will be delivered within '
                        u'three working days at the address you '
                        u'specified. We will deduct the fee for '
                        u'this card by direct debit.')

        mail_type_choice = MAIL_TYPE_SEND_USER_CARD
        # start fulfillment process
        Fulfillment.objects.create(
            profile=self.cc3_profile,
            card_registration=card_registration,
            status='New'
        )
        # send an email about the card request
        mail_card_admins(
            self.cc3_profile, mail_type_choice,
            translation.get_language())

        if message:
            messages.add_message(self.request, messages.INFO, message)
        return super(OwnerManageAndRegisterCardsView, self).form_valid(form)


class TransactionsXReport(ListView):
    context_object_name = 'cardtransaction_list'
    report_output_name = "x_report"

    def get_queryset(self):

        queryset = CardTransaction.objects.filter(
            models.Q(sender=self.request.user) |
            models.Q(receiver=self.request.user)
        ).filter(
            report_date__isnull=True
        )

        return queryset

    def get(self, request, *args, **kwargs):
        transactions = self.get_queryset()

        processed_transactions = []

        for trans in transactions:
            # TODO Add support for currencies with decimal points
            amount = int(trans.amount)

            trans_dict = SortedDict()
            trans_dict['date'] = "%s %s" % (date_format(trans.date_created,
                                                        use_l10n=True),
                                            time_format(trans.date_created,
                                                        use_l10n=True))
            trans_dict['operator'] = trans.operator.name
            if trans.operator.business == trans.receiver:
                trans_dict['amount +'] = "%s" % amount
                trans_dict['amount -/-'] = ""
            else:
                trans_dict['amount +'] = ""
                trans_dict['amount -/-'] = "-%s" % amount

            processed_transactions.append(trans_dict)

        if not processed_transactions:
            processed_transactions = [[]]
            headings = None
        else:
            headings = [
                ugettext('date'),
                ugettext('operator'),
                ugettext('amount +'),
                ugettext('amount -/-')
            ]

        return ExcelResponse(
            processed_transactions, force_csv=True,
            output_name=self.report_output_name, header_override=headings)


class TransactionsZReport(TransactionsXReport):
    report_output_name = "z_report"

    def get(self, request, *args, **kwargs):
        return_object = super(TransactionsZReport, self).get(
            request, *args, **kwargs)

        # mark transactions as reported on
        self.get_queryset().update(report_date=datetime.datetime.now())

        return return_object
