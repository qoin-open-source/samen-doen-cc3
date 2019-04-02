import calendar
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from io import BytesIO
import json
import logging
from xml.parsers.expat import ExpatError

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.mail import mail_admins
from django.db import models
from django.http import Http404, HttpResponse, HttpResponseRedirect, \
    HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.utils.datastructures import SortedDict
from django.utils.formats import date_format, time_format, number_format
from django.utils.translation import get_language, ugettext, ugettext_lazy as _
from django.views.generic import FormView, ListView, TemplateView, View
from django.views.generic.base import ContextMixin

from cc3.cyclos.forms import CC3ProfileForm
from cc3.cyclos.models import CC3Community, CC3Profile, User, CyclosGroup

from cc3.cyclos.services import (
    AccountNotFoundException, MemberNotFoundException)
from cc3.cyclos.common import TransactionException
from cc3.cyclos import backends
from cc3.excelexport.views import ExcelResponse
from cc3.mail.models import MailMessage, MAIL_TYPE_EXCHANGE_TO_MONEY
from cc3.marketplace.models import Ad, AdPaymentTransaction
from cc3.rewards.models import BusinessCauseSettings
from cc3.rewards.transactions import cause_reward

from .decorators import must_have_completed_profile
from .forms import (
    ApplyFullForm, CloseAccountForm, TradeQoinPayDirectForm,
    TradeQoinSplitPayDirectForm, TransactionsSearchForm, WantCreditForm,
    AccountSecurityForm, ExchangeToMoneyForm, TimeoutForm,
    TransactionsExportForm, ConfirmCloseAccountForm)
from .pdf import draw_transactions_pdf
from .utils import months_between, total_donations_originated_by_user


LOG = logging.getLogger('cc3.cyclos.account')


@login_required
def update_my_profile(request,
                      template_name='accounts/update_my_profile.html'):
    if request.user.is_superuser:
        return render_to_response(template_name, {
            'is_superuser': True
        }, context_instance=RequestContext(request))

    try:
        cc3_profile = CC3Profile.viewable.get(user=request.user)
    except CC3Profile.DoesNotExist:
        cc3_profile = None

    # update it POST and data is valid
    if request.method == "POST":
        form = CC3ProfileForm(request.POST, request.FILES,
                              instance=cc3_profile, user=request.user)

        if form.is_valid():
            cc3_profile = form.save()
            cc3_profile.update_slug()
            messages.add_message(
                request, messages.INFO, _('Details saved successfully.'))
            # add extra messages about matching categories if appropriate
            # Add the "safe" tag because they are HTML formatted
            for msg in cc3_profile.get_html_updated_categories_messages():
                messages.add_message(request, messages.INFO,
                                     msg, extra_tags="safe")
            # send the update categories email, if appropriate
            cc3_profile.send_updated_categories_email_if_needed()

            if request.is_ajax():
                return_object = {'success': True}
                return HttpResponse(
                    json.dumps(return_object), content_type='application/json')
            else:
                # must redirect
                return HttpResponseRedirect(
                    reverse('accounts-update-profile'))
        else:
            if request.is_ajax():
                form.errors['__all__'] = ugettext(
                    '''Unable to save your changes -
                    Please enter all required information and try again''')
                data = json.dumps(form.errors)
                response_kwargs = {
                    'status': 400,
                    'content_type': 'application/json'
                }
                return HttpResponse(data, **response_kwargs)
            else:
                messages.add_message(
                    request, messages.WARNING, _(
                        '''Unable to save your changes -
                        Please enter all required information and try again''')
                )

    else:
        form = None
        force_completion = getattr(settings, 'ACCOUNTS_FORCE_COMPLETION', True)
        has_completed_profile = CC3Profile.viewable.has_completed_profile(
            request.user)

        if force_completion and not has_completed_profile:
            messages.add_message(
                request, messages.WARNING,
                _('You must complete your profile in order to view other areas'
                  ' of your account'))
        if cc3_profile:
            form = CC3ProfileForm(instance=cc3_profile, user=request.user)

    latest_ads = offer_ads_count = wants_ads_count = None
    if cc3_profile:
        business_ads = Ad.objects.filter(
            created_by__slug=cc3_profile.slug, status='active')
        latest_ads = business_ads.order_by(
            '-date_created')[:settings.PROFILE_MAX_NUMBER_OF_LATEST_ADS]

        offer_ads = business_ads.filter(adtype__code__iexact='O')
        wants_ads = business_ads.filter(adtype__code__iexact='W')
        offer_ads_count = offer_ads.count()
        wants_ads_count = wants_ads.count()

    return render_to_response(template_name, {
        'form': form,
        'cc3_profile': cc3_profile,
        'latest_ads': latest_ads,
        'offer_ads_count': offer_ads_count,
        'wants_ads_count': wants_ads_count,
    }, context_instance=RequestContext(request))


class TransactionsViewMixin(ContextMixin):
    """
    Mixin class to add the ``available_balance`` and ``months`` list
    context variables to the transactions related views.
    """

    def get_context_data(self, **kwargs):
        """
        Adds the available balance for this account to the view context.
        """
        context = {}

        try:
            # super call can trigger the cyclos exceptions if it attempts to
            # get a pagination count of transactions for a cc3 user without a
            # cyclos account
            context = super(
                TransactionsViewMixin, self).get_context_data(**kwargs)
            account_status = backends.get_account_status(
                self.request.user.username)
            available_balance = account_status.accountStatus.availableBalance
        except AccountNotFoundException:
            LOG.error(u'Account {0} not found. No balance shown'.format(
                self.request.user.username))
            available_balance = None
        except MemberNotFoundException:
            LOG.error(u'Member {0} not found. No balance shown'.format(
                self.request.user.username))
            available_balance = None
        except TypeError:
            LOG.error(u'Backend returned None (which has no length). '
                      u'No balance shown'.format(
                        self.request.user.username))
            available_balance = None


        context['available_balance'] = available_balance

        now = datetime.now() - timedelta(days=30)
        months = months_between(now - timedelta(days=410), now)
        months.reverse()
        context['months'] = months

        return context


class TransactionsListView(TransactionsViewMixin, ListView):
    context_object_name = 'transactions'
    paginate_by = 10
    template_name = 'accounts/accounts_home.html'

    def get_queryset(self):
        """
        Overrides base ``get_queryset`` method to query Cyclos backend for
        transactions list.
        """
        try:
            return backends.transactions(
                self.request.user.username, direction='desc')
        except AccountNotFoundException:
            LOG.error(u'Account {0} not found. No transactions shown.'.format(
                self.request.user.username))
            return None
        except ExpatError:
            LOG.error(u'Backend error. No transactions shown.'.format(
                self.request.user.username))
            return None


class TransactionsSearchListView(TransactionsViewMixin, ListView):
    context_object_name = 'transactions'
    paginate_by = 10
    template_name = 'accounts/accounts_home.html'

    def get_transactions(self, form):
        # set queried_transactions to an empty list rather than None,
        queried_transactions = []

        if form.is_valid():
            try:
                transactions = backends.transactions(
                    self.request.user.username,
                    from_date=form.cleaned_data.get('from_date'),
                    to_date=form.cleaned_data.get('to_date'),
                    direction='desc')
            except AccountNotFoundException:
                LOG.error(u'Account {0} not found. No transactions '
                          u'shown.'.format(self.request.user.username))
                transactions = None

            try:
                # check there are transactions to iterate through,
                # otherwise the PageableTransactions are called multiple
                # times by the iterator to no avail (the for unit in trans bit)
                # check transactions isn't an empty list and there is a count()

                # set queried_transactions to an empty list rather than None,
                # so that paginator doesn't fail
                if transactions and transactions.count():
                    trans_type = form.cleaned_data.get('trans_type')
                    if trans_type == form.PAID:
                        for unit in transactions:
                            if unit and unit.amount < 0:
                                queried_transactions.append(unit)
                    elif trans_type == form.RECEIVED:
                        for unit in transactions:
                            if unit and unit.amount > 0:
                                queried_transactions.append(unit)
                    else:
                        queried_transactions = transactions

            # transaction.count() raises a MemberNotFoundException, if cyclos
            # doens't know the user
            except MemberNotFoundException:
                LOG.error(u'Account {0} not found. No transactions '
                          u'shown.'.format(self.request.user.username))

        return queried_transactions

    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('reset', '') == 'reset':
            return HttpResponseRedirect(
                reverse("accounts_transactions_search"))
        return super(TransactionsSearchListView,
                     self).dispatch(*args, **kwargs)

    def get_queryset(self):
        form = TransactionsSearchForm(self.request.GET)
        if form.is_valid():
            return self.get_transactions(form)
        else:
            return []

    def get_context_data(self, **kwargs):
        context = super(TransactionsSearchListView, self).get_context_data(
            **kwargs)
        context['menu_form'] = TransactionsSearchForm(self.request.GET or None)

        return context


class TransactionsExportView(TransactionsSearchListView):
    """
    Inherit from search view, but use export form due to
    duplicate ids being invalid in HTML
    """

    def get_queryset(self):
        form = TransactionsExportForm(self.request.GET)
        return self.get_transactions(form)

    def get_context_data(self, **kwargs):
        """
        no need for any context
        """
        return None

    def get(self, request, *args, **kwargs):
        headings = None
        export_transactions = self.get_queryset()
        if len(export_transactions) == 0:
            export_transactions_p = [export_transactions]
        else:
            # massage the data
            export_transactions_p, headings = self.process_export_transactions(
                export_transactions)

        return ExcelResponse(export_transactions_p, force_csv=True,
                             output_name="transactions",
                             header_override=headings)

    def process_export_transactions(self, transactions):
        """
        Convert raw object list transactions into format as per template
        """
        processed_transactions = []

        for trans in transactions:

            if trans.amount < 0:
                try:
                    du_au = trans.recipient.get_profile().full_name
                except:
                    try:
                        du_au_user = User.objects.get(username=trans.recipient)
                        du_au = du_au_user.get_profile().full_name
                    except:
                        du_au = trans.recipient
            else:
                try:
                    du_au = trans.sender.get_profile().full_name
                except:
                    try:
                        du_au_user = User.objects.get(username=trans.sender)
                        du_au = du_au_user.get_profile().full_name
                    except:
                        du_au = trans.sender

            trans_dict = SortedDict()
            trans_dict['date'] = "%s %s" % (date_format(trans.created,
                                                        use_l10n=True),
                                            time_format(trans.created,
                                                        use_l10n=True))
            trans_dict['from/to'] = du_au
            trans_dict['description'] = trans.description
            trans_dict['amount'] = number_format(trans.amount, 2)

            processed_transactions.append(trans_dict)

        headings = [
            ugettext('date'),
            ugettext('from/to'),
            ugettext('description'),
            ugettext('amount')
        ]

        return processed_transactions, headings


class TransactionsDownloadView(ListView):
    """
    Replicated elements of AccountView to separate out
    download views from other logic
    """

    def get_user(self):
        """
        **DO NOT REMOVE**, as it can be used by community admin views
        to select different users
        """
        return self.request.user

    def get_transactions(self, from_date=None, to_date=None, direction='desc'):
        user = self.get_user()
        try:
            return backends.transactions(
                user.username,
                from_date=from_date,
                to_date=to_date,
                direction=direction
            )
        except AccountNotFoundException:
            return None


class TransactionsMonthlyPDFView(TransactionsDownloadView):
    def get(self, request, *args, **kwargs):
        now = datetime.now() - timedelta(days=30)
        # TODO 'months' is in context of TransactionListView,
        # ie context['months'],
        # so would be better to have a single utility function
        months = months_between(now - timedelta(days=410), now)
        months.reverse()
        month = months[int(request.GET.get('month'))]

        next_month = month + timedelta(
            days=calendar.monthrange(month.year, month.month)[1])
        transactions = self.get_transactions(
            from_date=month, to_date=next_month)
        output = BytesIO()
        draw_transactions_pdf(
            output, self.request.user, transactions, month=month)

        resp = HttpResponse(content_type='application/pdf')
        resp.content = output.getvalue()
        resp['Content-Disposition'] = \
            u'attachment; filename="{0}-{1}-{2}.pdf"'.format(
                _('monthly_statement'), str(month.month), str(month.year))
        return resp


class TransactionsLast10PDFView(TransactionsDownloadView):
    def get(self, request, *args, **kwargs):
        today = datetime.today()
        transactions = self.get_transactions()[:10]
        output = BytesIO()
        current_balance = self.get_user().cc3_profile.current_balance
        draw_transactions_pdf(
            output, self.request.user, transactions,
            current_balance=current_balance)

        resp = HttpResponse(content_type='application/pdf')
        resp.content = output.getvalue()
        resp['Content-Disposition'] = \
            u'attachment; filename="{0}-{1}-{2}-{3}.pdf"'.format(
                _('last_10_transactions'), str(today.day), str(today.month),
                str(today.year))
        return resp


class AccountsView(ListView):
    """
    Used in ``communityadmin.MemberTransactionsView``.

    TODO: DEPRECATE this whole class and rewrite smaller views for each
    function of the class, like we already did for the 'get transactions
    table' and 'search for transactions'

    - View `get_monthly_pdf`: Just a view returning the monthly PDF doc.
    - View `last_10_transactions_pdf`: Another view to return the last 10
    transactions PDF doc.

    ...etc.
    """
    context_object_name = 'transactions'
    paginate_by = 10
    extra_context = None
    extra_message = None

    def get_user(self):
        return self.request.user

    def get_transactions(self, from_date=None, to_date=None, direction='desc'):
        user = self.get_user()
        try:
            return backends.transactions(
                user.username,
                from_date=from_date,
                to_date=to_date,
                direction=direction
            )
        except AccountNotFoundException:
            return None

    def get_queryset(self):
        # need to do sorting / filtering here
        # filtering - if valid form POST
        # save last POST to session for use in sorted / ordered view
        from_date = self.request.session.get('from_date', None)
        to_date = self.request.session.get('to_date', None)

        # sorting / ordering
        field = 'date'
        direction = getattr(settings, 'ACCOUNTS_VIEW_ORDER', 'asc')
        if self.args and len(self.args) == 2:
            # need some sanitising - only allowing date ordering atm if that
            if self.args[0] == 'date':
                field = self.args[0]
            if self.args[1] == 'asc' or self.args[1] == 'desc':
                direction = self.args[1]
        transactions = self.get_transactions(from_date, to_date, direction)

        return transactions

    def reset_search_form(self):
        form = TransactionsSearchForm()
        self.request.session['from_date'] = None
        self.request.session['to_date'] = None
        return form

    def perform_search_form(self):
        form = TransactionsSearchForm(self.request.POST)

        # set some kwargs for the query set filtering
        if form.is_valid():
            self.request.session['from_date'] = form.cleaned_data['from_date']
            self.request.session['to_date'] = form.cleaned_data['to_date']
        return form

    def get_monthly_pdf(self, month):
        next_month = month + timedelta(
            days=calendar.monthrange(month.year, month.month)[1])
        transactions = self.get_transactions(
            from_date=month, to_date=next_month)
        output = BytesIO()
        draw_transactions_pdf(
            output, self.request.user, transactions, month=month)

        resp = HttpResponse(content_type='application/pdf')
        resp.content = output.getvalue()
        resp['Content-Disposition'] = \
            u'attachment; filename="{0}-{1}-{2}.pdf"'.format(
                _('monthly_statement'), str(month.month), str(month.year))
        return resp

    def get_last_10_transactions_pdf(self):
        today = datetime.today()
        transactions = self.get_transactions()[:10]
        output = BytesIO()
        current_balance = self.get_user().cc3_profile.current_balance
        draw_transactions_pdf(
            output, self.request.user, transactions,
            current_balance=current_balance)

        resp = HttpResponse(content_type='application/pdf')
        resp.content = output.getvalue()
        resp['Content-Disposition'] = \
            u'attachment; filename="{0}-{1}-{2}-{3}.pdf"'.format(
                _('last_10_transactions'),
                str(today.day), str(today.month), str(today.year)
            )
        return resp

    def get(self, request, *args, **kwargs):
        now = datetime.now() - timedelta(days=30)
        months = months_between(now - timedelta(days=410), now)
        months.reverse()
        if request.method == 'POST':
            if request.POST.get('action', '') == 'search':
                if 'reset' in request.POST and \
                        request.POST['reset'] == u'reset':
                    form = self.reset_search_form()
                else:
                    form = self.perform_search_form()
            elif request.POST.get('action', '') == 'monthly_pdf':
                return self.get_monthly_pdf(months[int(
                    request.POST.get('month'))])
            elif request.POST.get('action', '') == 'last_10_pdf':
                return self.get_last_10_transactions_pdf()

            if 'reset' in request.POST and \
                    request.POST['reset'] == u'reset':
                form = TransactionsSearchForm()
                self.request.session['from_date'] = None
                self.request.session['to_date'] = None
            else:
                form = TransactionsSearchForm(request.POST)

                # set some kwargs for the query set filtering
                if form.is_valid():
                    self.request.session['from_date'] = \
                        form.cleaned_data['from_date']
                    self.request.session['to_date'] = \
                        form.cleaned_data['to_date']
        else:
            from_date = self.request.session.get('from_date', None)
            to_date = self.request.session.get('to_date', None)

            if from_date or to_date:
                form_data = {
                    'from_date': from_date,
                    'to_date': to_date,
                }

                form = TransactionsSearchForm(form_data)
            else:
                form = TransactionsSearchForm()

        # from CBV BaseListView
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            if (self.get_paginate_by(self.object_list) is not None
                    and hasattr(self.object_list, 'exists')):
                is_empty = not self.object_list.exists()
            else:
                is_empty = len(self.object_list) == 0
            if is_empty:
                raise Http404(_(
                    """Empty list and '%(class_name)s.allow_empty' is False."""
                ) % {'class_name': self.__class__.__name__})

        context = self.get_context_data(object_list=self.object_list, **kwargs)

        # inject validated form and filters
        context['account_search_form'] = form
        context['months'] = months
        if self.args and len(self.args) == 2:
            context['account_search_form_field'] = self.args[0]
            context['account_search_form_direction'] = self.args[1]
        else:
            context['account_search_form_field'] = 'date'
            context['account_search_form_direction'] = 'desc'

        if 'export' in request.POST and \
                request.POST['export'] == u'export':
            headings = None
            export_transactions = self.object_list
            if len(export_transactions) == 0:
                export_transactions_p = [export_transactions]
            else:
                # massage the data
                export_transactions_p, headings = \
                    self.process_export_transactions(export_transactions)

            return ExcelResponse(export_transactions_p, force_csv=True,
                                 output_name="transactions",
                                 header_override=headings)

        return self.render_to_response(context)

    def process_export_transactions(self, transactions):
        """
        Convert raw object list transactions into format as per template
        TODO would be neater to use same template for both HTML and CSV
        """
        processed_transactions = []

        for trans in transactions:

            if trans.amount < 0:
                try:
                    du_au = trans.recipient.get_profile().full_name
                except:
                    try:
                        du_au_user = User.objects.get(username=trans.recipient)
                        du_au = du_au_user.get_profile().full_name
                    except:
                        du_au = trans.recipient
            else:
                try:
                    du_au = trans.sender.get_profile().full_name
                except:
                    try:
                        du_au_user = User.objects.get(username=trans.sender)
                        du_au = du_au_user.get_profile().full_name
                    except:
                        du_au = trans.sender

            trans_dict = SortedDict()
            trans_dict['date'] = "%s %s" % (date_format(trans.created,
                                                        use_l10n=True),
                                            time_format(trans.created,
                                                        use_l10n=True))
            trans_dict['from/to'] = du_au
            trans_dict['description'] = trans.description
            trans_dict['amount'] = number_format(trans.amount, 2)

            processed_transactions.append(trans_dict)

        headings = [_('date'), _('from/to'), _('description'), _('amount')]

        return processed_transactions, headings

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        try:
            context = super(AccountsView, self).get_context_data(**kwargs)
        except AccountNotFoundException:
            context = {}
        except MemberNotFoundException:
            context = {}

        try:
            account_status = backends.get_account_status(
                self.get_user().username)
            available_balance = account_status.accountStatus.availableBalance
            context['account_not_found'] = False
        except AccountNotFoundException:
            available_balance = None
        except MemberNotFoundException:
            available_balance = None

        context['available_balance'] = available_balance
        context['account_not_found'] = True if available_balance is None \
            else False

        # TODO - why are we counting these and not the transactions we display?
        # SW: We store a history of member to member transactions in django
        # Cyclos also has System to member transactions.
        # To include these, we'd need an additional cyclos webservice call per
        # context refresh
        trans = AdPaymentTransaction.objects.filter(
            models.Q(sender=self.request.user) |
            models.Q(receiver=self.request.user))
        if trans:
            context['number_of_transactions'] = trans.count()
        else:
            context['number_of_transactions'] = 0

        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value
        return context


class PayDirectFormView(FormView):
    template_name = 'accounts/pay_direct.html'
    success_url = reverse_lazy('accounts_home')
    split_payments = False

    def get_form(self, form_class):
        """
        Overrides the base ``get_form`` method. Returns a specific form
        regarding the permission of the user to make split payments or not. It
        will return ``None`` (no form at all) if the user is not able to
        perform payments. Thus, a proper message should be shown in template.
        """
        cc3_profile = self.request.user.get_cc3_profile()

        if cc3_profile and cc3_profile.web_payments_enabled:
            kwargs = self.get_form_kwargs()
            kwargs['user'] = self.request.user
            payee = self.request.GET.get('pay', None)
            if payee:
                try:
                    data = {}
                    payee_profile = CC3Profile.objects.get(user__username=payee)
                    data['profile'] = payee_profile.pk
                    if payee_profile.business_name:
                        data['contact_name'] = "{0} {1} ({2})".format(
                            payee_profile.first_name,
                            payee_profile.last_name,
                            payee_profile.business_name
                        )
                    else:
                        data['contact_name'] = "{0} {1}".format(
                            payee_profile.first_name,
                            payee_profile.last_name
                        )
                    kwargs['data'] = data

                except CC3Profile.DoesNotExist:
                    pass
            if self.request.user.cc3_profile.split_payments_allowed():
                self.split_payments = True
                return TradeQoinSplitPayDirectForm(**kwargs)
            else:
                return TradeQoinPayDirectForm(**kwargs)

        return None

    def _perform_payment(self, data):
        sender = self.request.user
        receiver = data['profile'].user
        amount = data['amount']
        description = data['description']
        split_total = None if not self.split_payments else data['total_value']
        transaction_id = None

        try:
            # Cyclos transaction request.
            transaction = backends.user_payment(
                sender, receiver, amount, description)
            messages.add_message(
                self.request, messages.SUCCESS,
                _('Payment made successfully.'))
            transaction_id = transaction.transfer_id
        except TransactionException, e:
            error_message = _('Could not make payment at this time.')

            if 'NOT_ENOUGH_CREDITS' in e.args[0]:
                error_message = _('You do not have sufficient credit to '
                                  'complete the payment plus the '
                                  'transaction fee.')
            messages.add_message(self.request, messages.ERROR, error_message)
        else:
            try:
                # Log the payment
                AdPaymentTransaction.objects.create(
                    title=description[0:255],
                    amount=amount,
                    sender=sender,
                    receiver=receiver,
                    transfer_id=transaction.transfer_id,
                    split_payment_total_amount=split_total
                )
            except Exception, e:
                # Report this to ADMINS, but show success to user
                # because the payment was made
                message = u'Direct payment made (transfer id={0}), but '  \
                    u'failed to create AdPaymentTransaction: {1}'.format(
                                                transaction.transfer_id, e)
                LOG.error(message)

                if not settings.DEBUG:
                    mail_admins(u'Failed to log payment',
                                message, fail_silently=True)

        return transaction_id

    def _perform_reward_payment(self, data, transaction_id):
        sender = self.request.user
        profile = sender.get_profile()
        # NB. transaction_id parameter is actually the cyclos transfer_id

        # current requirement is only to make reward payment
        # if sender is 'Instelligen' #2481
        # if businesses ever get the 'direct payment' view to individuals then
        # they will need to make the reward payment
        if profile.is_institution_profile():
            receiver = data['profile'].user
            amount = data['amount']
            reward = cause_reward(amount, receiver, transaction_id)
            if reward:
                LOG.info(u'Donation transferred, transaction: {0}'.format(
                    reward.transfer_id))
            else:
                message = u'Donation payment failed from sender {0} to ' \
                          u'receiver {1} for amount {2}'.format(sender,
                                                                receiver,
                                                                amount)
                LOG.error(message)

                if not settings.DEBUG:
                    mail_admins(u'Failed to make donation payment',
                                message, fail_silently=True)

    def form_valid(self, form):
        # prevent duplicate payments if using modal dialog box
        # with confirmation (and timeout for double clicks)
        if self.request.is_ajax():
            # if we're dealing with ajax, wait for 2nd submit,
            # where POST has 'confirmed key'
            if not 'confirmed' in self.request.POST:
                data = json.dumps({
                    'success': True,
                    'full_name': form.cleaned_data['profile'].full_name})
                return HttpResponse(data, {
                    'content_type': 'application/json',
                })

        transaction_id = self._perform_payment(form.cleaned_data)
        if 'cc3.rewards' in settings.INSTALLED_APPS:
            self._perform_reward_payment(form.cleaned_data, transaction_id)

        return super(PayDirectFormView, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            data = json.dumps(form.errors)
            response_kwargs = {
                'status': 400,
                'content_type': 'application/json'
            }
            return HttpResponse(data, **response_kwargs)

        return super(PayDirectFormView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(PayDirectFormView, self).get_context_data(**kwargs)
        context['split_payments'] = self.split_payments
        context['min_contact_auto'] = getattr(
            settings, "CONTACT_AUTO_MINIMUM_CHARS", 1)
        return context


@login_required
@must_have_completed_profile
def want_credit_view(request, form_class=WantCreditForm,
                     template_name='accounts/credit.html', success_url=None,
                     extra_context=None, fail_silently=False):
    """
    Taken from django contact form. might not be necessary
    (ie just use contact form view?)...
    """
    group_id = backends.get_group(request.user.email)
    if group_id == backends.get_member_group_id():
        return apply_full_view(
            request, success_url=success_url, extra_context=extra_context,
            fail_silently=fail_silently)

    if success_url is None:
        success_url = reverse('accounts-credit-sent')
    if request.method == 'POST':
        form = form_class(
            data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save(fail_silently=fail_silently)
            return HttpResponseRedirect(success_url)
    else:
        form_data = {}
        if request.user.is_authenticated():
            cc3_profile = CC3Profile.viewable.get(
                user=request.user
            )
            form_data = {
                "name": cc3_profile.full_name,
                "email": request.user.email,
            }
        form = form_class(initial=form_data, request=request)

    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    # NB need to use availableBalance here really - as overdrafts are possible
    account_status = backends.get_account_status(request.user.username)
    credit_limit = account_status.accountStatus.creditLimit
    available_balance = account_status.accountStatus.availableBalance

    return render_to_response(
        template_name,
        {
            'form': form,
            'credit_limit': credit_limit,
            'available_balance': available_balance
        },
        context_instance=context)


@login_required
@must_have_completed_profile
def apply_full_view(
        request, form_class=ApplyFullForm, template_name='accounts/apply.html',
        success_url=None, extra_context=None, fail_silently=False):
    """
    Taken from django contact form. might not be necessary
    (ie just use contact form view?)...
    """

    if success_url is None:
        success_url = reverse('accounts-apply-sent')
    if request.method == 'POST':
        form = form_class(
            data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save(fail_silently=fail_silently)
            return HttpResponseRedirect(success_url)
    else:
        form_data = {}
        if request.user.is_authenticated():
            cc3_profile = CC3Profile.viewable.get(
                user=request.user
            )
            form_data = {
                "name": cc3_profile.full_name,
                "email": request.user.email,
            }
        form = form_class(initial=form_data, request=request)

    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(
        template_name, {'form': form}, context_instance=context)


class CloseAccountView(FormView):
    template_name = 'accounts/close_account.html'
    form_class = CloseAccountForm
    extra_context = None

    def get_success_url(self):
        return reverse('accounts_home')

    def form_valid(self, form):
        # set profile to pending closure
        cc3_profile = self.request.user.get_profile()
        cc3_profile.is_pending_closure = True
        cc3_profile.date_closure_requested = datetime.now()
        cc3_profile.save()
        return HttpResponseRedirect(self.get_success_url())


class ReallyCloseAccountView(FormView):
    template_name = 'accounts/really_close_account.html'
    form_class = ConfirmCloseAccountForm
    extra_context = None

    def __init__(self):
        super(ReallyCloseAccountView, self).__init__()

    def dispatch(self, request, *args, **kwargs):
        # check whether user is allowed to close own account
        self.user = self.request.user
        self.cc3_profile = self.user.get_profile()
        cyclos_group = self.cc3_profile.get_cyclos_group()

        permitted_groupnames = getattr(settings,
                                       'GROUPS_ALLOWED_TO_CLOSE_ACCOUNT', [])
        if cyclos_group.name in permitted_groupnames:
            return super(ReallyCloseAccountView, self).dispatch(
                request, *args, **kwargs)
        else:
            LOG.info(u'Invalid attempt to close account by user {0}. '
                     u'Cyclos group is {1}'.format(
                    self.user.username, cyclos_group.name))
            raise PermissionDenied

    def get_form(self, form_class):
        return form_class(user=self.user, **self.get_form_kwargs())

    def get_success_url(self):
        return reverse('accounts_really_close_done')

    def form_valid(self, form):
        self.cc3_profile.close_account()
        logout(self.request)
        return HttpResponseRedirect(self.get_success_url())


class AddFunds(TemplateView):
    template_name = 'marketplace/add_funds.html'

    def get_context_data(self, **kwargs):
        # First check that we have the necessary settings.
        if not getattr(settings, 'PAYPAL_DOMAIN', None):
            raise ImproperlyConfigured(
                u"Please provide a PAYPAL_DOMAIN in the project settings.")

        if not getattr(settings, 'PAYPAL_BUTTON_ID', None):
            raise ImproperlyConfigured(
                u"Please provide a PAYPAL_BUTTON_ID in the project settings.")

        ctx = super(AddFunds, self).get_context_data(**kwargs)

        def _get_cyclos_username(search_email):
            for c_id, name, email, username, group in backends.search(
                    email=search_email):
                if search_email == email:
                    return username

        ctx['sbmenu'] = "add-funds"
        ctx['cyclos_username'] = _get_cyclos_username(self.request.user.email)
        ctx['paypal_domain'] = settings.PAYPAL_DOMAIN
        ctx['paypal_button_id'] = settings.PAYPAL_BUTTON_ID
        return ctx


class ExchangeToMoneyView(FormView):
    """
    Allows a user to make a system to "real" money transaction.
    """
    TRANSFER_TYPE_ID = 38
    template_name = 'accounts/exchange_to_money.html'
    form_class = ExchangeToMoneyForm
    success_url = reverse_lazy('exchange-to-money')

    def _get_cyclos_username(self, search_email):
        for c_id, name, email, username, group in backends.search(
                email=search_email):
            if search_email == email:
                return username

    def get_form_kwargs(self):
        kwargs = super(ExchangeToMoneyView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        amount = form.cleaned_data['amount']
        # Make cyclos payment.
        sender = self.request.user
        description = u"System to money transfer."
        transfer_type_id = getattr(settings,
                    'CYCLOS_EXCHANGE_TO_MONEY_TRANSFER_TYPE_ID',
                    ExchangeToMoneyView.TRANSFER_TYPE_ID)

        backends.to_system_payment(
            sender, amount, description, transfer_type_id)

        messages.add_message(self.request,  messages.INFO,
                            _('Transaction successful'))

        # if an email template exists, send email to admins
        try:
            self.admins_msg = MailMessage.objects.get_msg(
                MAIL_TYPE_EXCHANGE_TO_MONEY, lang=get_language())
        except MailMessage.DoesNotExist:
            self.admins_msg = None
        if self.admins_msg:
            site = Site.objects.get_current()
            profile_edit_url = "http://{0}{1}".format(
                                    Site.objects.get_current().domain,
                                    reverse('communityadmin_ns:editmember',
                                    kwargs={'username': sender.username}))
            context = {'sender': sender,
                       'amount': amount,
                       'description': description,
                       'profile_edit_url': profile_edit_url}
            for comm_admin in sender.get_community().get_administrators():
                try:
                    self.admins_msg.send(comm_admin.user.email, context)
                except Exception as e:
                    LOG.error('Failed to send exchange to money email '
                              'to community admin {0}: {1}'.format(
                                                        comm_admin.pk, e))

        return HttpResponseRedirect(self.get_success_url())


# AJAX info views
def contact_name_auto(request, community=None):
    """
    Returns contact name with business for valid email address.
    Returns data for the autocomplete field.

    Data is formatted as lines with three columns separated by tabs:
        1. Completion data.
        2. Formatted data.
        3. URL.
    """
    if not request.is_ajax():
        return HttpResponseForbidden(_('This is only available to web pages'))

    contact_name_filter = request.GET.get('contact_name')
    min_contact_name_auto = getattr(settings, "CONTACT_AUTO_MINIMUM_CHARS", 1)
    if len(contact_name_filter) < min_contact_name_auto:
        return HttpResponse('[]', content_type='application/json')

    # take a chance and remove anything after a bracket,
    # as likely to be business name returned by this function
    if '(' in contact_name_filter:
        contact_name_filter = contact_name_filter[:contact_name_filter.find(
            '(') - 1]

    businesses = CC3Profile.viewable.all()
    for term in contact_name_filter.split():
        businesses = businesses.filter(
            models.Q(business_name__icontains=term) |
            models.Q(last_name__icontains=term) |
            models.Q(first_name__icontains=term)
        )

    businesses = businesses.exclude(user=request.user).distinct().order_by(
        'first_name', 'last_name')

    profile = request.user.get_profile()
    if community:
        inter_communities_transactions_allowed = \
            profile.inter_communities_transactions_allowed()
    else:
        inter_communities_transactions_allowed = True

    if not inter_communities_transactions_allowed:
        community = get_object_or_404(CC3Community, pk=community)
        if request.user.cc3_profile.community != community:
            # Users cannot perform operations in foreign communities.
            raise Http404

        businesses = businesses.filter(community=community)

    business_names = businesses.distinct().values_list(
        'pk',
        'first_name',
        'last_name',
        'business_name',
    )

    data = []
    for e in business_names:
        if e[3]:
            data.append({
                'pk': e[0], 'value': u'{0} {1} ({2})'.format(e[1], e[2], e[3])
            })
        else:
            data.append({'pk': e[0], 'value': u'{0} {1}'.format(e[1], e[2])})

    data.sort()
    json_data = json.dumps(data)

    return HttpResponse(json_data, content_type='application/json')


class PostLoginView(View):
    """
    Redirect staff members directly to the Django admin
    Redirect community admins directly to the communityadmin memberlist.
    All other users are sent to their homepage.
    """

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            if request.user.is_staff:
                return HttpResponseRedirect(reverse('admin:index'))
            if request.user.is_community_admin():
                return HttpResponseRedirect(
                    reverse('communityadmin_ns:memberlist'))
        redirect_to = request.GET.get('redirect_to', False)
        if redirect_to:
            return HttpResponseRedirect(redirect_to)
        return HttpResponseRedirect(reverse('accounts_home'))


class AccountSecurityView(FormView):
    template_name = 'accounts/accounts_security.html'
    form_class = AccountSecurityForm
    success_url = reverse_lazy('accounts_security')
    extra_context = None

    def get_form(self, form_class):
        return form_class(user=self.request.user, **self.get_form_kwargs())

    def form_valid(self, form):
        form.update_channels()
        return super(AccountSecurityView, self).form_valid(form)


class AccountStatsView(TemplateView):
    template_name = 'accounts/account_stats_summary.html'

    def get_euros_from_amount_spent(self, reward_amount):
        """
        Returns the amount of euros that must have been spent by a
        customer to result in a payment of reward_amount
        """
        if 'cc3.rewards' not in settings.INSTALLED_APPS:
            return None

        # Determine what sort of reward was paid
        reward_percentage = Decimal("5.00")
        reward_type = 'percentage'
        try:
            business_settings = BusinessCauseSettings.objects.get(
                user=self.request.user)
            if not business_settings.reward_percentage:
                reward_type = 'fixed'
            elif business_settings.transaction_percentage > 0:
                reward_percentage = business_settings.transaction_percentage
        except BusinessCauseSettings.DoesNotExist:
            LOG.error(u'Business {0} has no settings defined'.format(
                self.request.user))
        if reward_type == 'fixed':
            LOG.error(u'Business {0} has fixed reward amount. '
                      u'Cannot determine euro amount'.format(
                self.request.user))
            return None

        euro_conversion_rate = getattr(settings,
                                       'CC3_CURRENCY_CONVERSION', None)
        if euro_conversion_rate:
            return ((reward_amount * Decimal(100.0) / reward_percentage)
                / Decimal(euro_conversion_rate))

        return None

    def get_month_key(self, transaction):
        check_date = transaction.created
        if (check_date.year == self.PREVIOUS_MONTH.year and
                check_date.month == self.PREVIOUS_MONTH.month):
            return 'previous'
        if (check_date.year == self.THIS_MONTH.year and
                check_date.month == self.THIS_MONTH.month):
            return 'this'
        return None

    def get_context_data(self, **kwargs):
        # TODO: First check that view is relevant to this user
        # Currently only Business users have this view
        # ... but what's the cc3-safe check for business ?

        ctx = super(AccountStatsView, self).get_context_data(**kwargs)

        amount_redeemed = {'this': 0, 'previous': 0}
        amount_spent = {'this': 0, 'previous': 0}
        num_transactions = {'this': 0, 'previous': 0}
        num_spend_transactions = {'this': 0, 'previous': 0}
        unique_customers = {'this': {}, 'previous': {},}
        total_amount_spent = 0

        redeem_transfer_type_id = getattr(
            settings, 'REDEEM_TRANSFER_TYPE_ID', 31)
        spend_transfer_type_id = getattr(
            settings, 'SPEND_TRANSFER_TYPE_ID', 35)

        self.THIS_MONTH = date.today()
        self.PREVIOUS_MONTH = self.THIS_MONTH + relativedelta(months=-1)
        first_of_previous_month = date(day=1,
            year=self.PREVIOUS_MONTH.year, month=self.PREVIOUS_MONTH.month)

        # get all transactions for this user
        try:
            transactions = backends.transactions(
                self.request.user.username,
                direction='desc',
                from_date=first_of_previous_month)
        except AccountNotFoundException:
            LOG.error(u'Account {0} not found. No transactions '
                      u'shown.'.format(self.request.user.username))
            transactions = None

        try:

            # check there are transactions to iterate through,
            # check transactions isn't an empty list and there is a count()
            if transactions and transactions.count():
                for trans in transactions:
                    LOG.debug(trans)
                    date_key = self.get_month_key(trans)
                    if date_key:
                        num_transactions[date_key] += 1
                        if trans.transfer_type_id == redeem_transfer_type_id:
                            unique_customers[date_key][trans.sender] = 1
                            amount_redeemed[date_key] += trans.amount
                        if trans.transfer_type_id == spend_transfer_type_id:
                            unique_customers[date_key][trans.recipient] = 1
                            amount_spent[date_key] -= trans.amount
                            num_spend_transactions[date_key] += 1

        # transaction.count() raises a MemberNotFoundException, if cyclos
        # doesn't know the user
        except MemberNotFoundException:
            LOG.error(u'Account {0} not found. No transactions '
                      u'shown.'.format(self.request.user.username))

        ctx['amount_redeemed'] = {}
        ctx['amount_spent'] = {}
        ctx['num_transactions'] = {}
        ctx['unique_customers'] = {}
        ctx['total_euros'] = {}
        ctx['average_euros'] = {}
        for key in ['this', 'previous']:
            ctx['amount_redeemed'][key] = amount_redeemed[key]
            ctx['amount_spent'][key] = amount_spent[key]
            ctx['num_transactions'][key] = num_transactions[key]
            ctx['unique_customers'][key] = len(unique_customers[key])
            ctx['total_euros'][key] = self.get_euros_from_amount_spent(
                amount_spent[key])
            if num_spend_transactions[key]:
                ctx['average_euros'][key] = (ctx['total_euros'][key] /
                                             num_spend_transactions[key])
            else:
                ctx['average_euros'][key] = 0
        # donations to good causes = 40% of amount_spent
        fixed_reward_percentage = getattr(settings,
                                          'REWARDS_FIXED_PERCENTAGE', 40)
        ctx['total_donations'] = total_donations_originated_by_user(
            self.request.user.username)
        return ctx


class TimeoutView(FormView):
    form_class = TimeoutForm

    def get(self, request, *args, **kwargs):
        messages.add_message(
            request, messages.WARNING, _(
                'You have been logged out, following a period of inactivity.'))

        return HttpResponseRedirect(reverse('auth_logout'))
