import json
import os
from string import ascii_letters, digits

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import intcomma
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import loader
from django.template.context import RequestContext
from django.template.defaultfilters import slugify
from django.utils.datastructures import SortedDict
from django.utils.decorators import method_decorator
from django.utils.formats import date_format, time_format
from django.utils.translation import ugettext, ugettext_lazy as _
from django.views.generic import ListView, UpdateView, TemplateView, CreateView

from formtools.wizard.views import SessionWizardView
from registration.models import RegistrationProfile

from cc3.accounts.views import AccountsView
from cc3.cyclos import backends
from cc3.core.models import Category
from cc3.cyclos.models import (
    User, CC3Profile, CyclosAccount, CommunityMessage, CyclosGroup,
    CommunityRegistrationCode, CC3Community)
from cc3.cyclos.forms import CC3ProfileForm
from cc3.excelexport.views import ExcelResponse
from cc3.marketplace.forms import AdImageFormSet
from cc3.marketplace.models import (
    Ad, AdImage, AdPaymentTransaction, PreAdImage)
from cc3.marketplace.views import MarketplaceAdDisableView
from cc3.marketplace.views import MarketplaceAdUpdateView
from cc3.registration.forms import TradeQoinRegistrationForm

from .models import CommunityMember
from .sql.profile import (
    COMMUNITY_MEMBER_LIST, COMMUNITY_MEMBER_LIST_WHERE_EXTRA)
from .forms import (
    OffersWantsForm, CommunityMessageForm, ChangeGroupForm, AdHoldForm,
    CommunityAdminAdForm, CommunityAdminCreatedByForm,
    CommunityAdminAdUpdateForm, CommunityAdminCategoriesForm)

import logentry_auditlog_admin as log


class CommunityMixin(object):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        """
        Ensures the user is logged in and filters all the users who are not a
        community administrator.
        """
        community = request.user.get_admin_community()
        if not community:
            log.user_action(
                request, request.user,
                'Tried to access community admin section without '
                'permissions.')
            raise PermissionDenied

        return super(CommunityMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Adds the community for which this user is an admin to the request
        context.
        """
        context = super(CommunityMixin, self).get_context_data(**kwargs)
        context['community'] = self.request.user.get_admin_community()

        return context


class ContentListView(CommunityMixin, ListView):
    model = CommunityMessage
    template_name = 'communityadmin/content_list.html'
    paginate_by = 10
    context_object_name = 'community_messages'

    def get_queryset(self):
        community = self.request.user.get_admin_community()

        message_list = CommunityMessage.objects.filter(
            community=community,
            plugin__placeholder__page__publisher_is_draft=True
        ).order_by('plugin__placeholder')

        return message_list


class EditContent(CommunityMixin, UpdateView):
    model = CommunityMessage
    template_name = 'communityadmin/content_edit.html'
    form_class = CommunityMessageForm

    def get_success_url(self):
        return reverse('communityadmin_ns:contentlist')


class MemberListView(CommunityMixin, ListView):
    model = CommunityMember
    template_name = 'communityadmin/member_list.html'
    paginate_by = 10
    context_object_name = 'members'

    def get_queryset(self, *args, **kwargs):
        """
        Returns a list with all the members of the current community.

        """
        community = self.request.user.get_admin_community()

        # sorting / ordering
        field = 'date_joined'
        direction = 'desc'
        if args and len(args) == 2:
            field = args[0]
            direction = args[1]

        if direction not in ['asc', 'desc']:
            raise PermissionDenied()

        if field not in ['last_name', 'first_name', 'business_name',
                         'company_website', 'offers', 'wants', 'active_ads',
                         'date_joined']:
            raise PermissionDenied()
        if field in ['offers', 'wants', 'active_ads']:
            field = u'count_{0}'.format(field)

        member_list_query = COMMUNITY_MEMBER_LIST
        member_list_params = [community.id]  # which community
        query = self.request.GET.get('q')
        if query:
            query = u"%{0}%".format(self.request.GET.get('q'))
            member_list_query = u"{0} {1}".format(
                member_list_query,
                COMMUNITY_MEMBER_LIST_WHERE_EXTRA
            )
            member_list_params = member_list_params + [
                query, query, query, query]

        # use raw to get better ordering capabilities
        member_list_query = u"{0} ORDER BY {1} {2}".format(
            member_list_query, field, direction)
        member_list = CommunityMember.objects.raw(
            member_list_query, member_list_params)

        return list(member_list)

    def get_context_data(self, **kwargs):
        context = super(MemberListView, self).get_context_data(**kwargs)
        context['balance_alert_limit'] = getattr(
            settings, 'TRACK_LARGE_BALANCE_LIMIT', None)
        # DRY violated...
        context['sort_field'] = 'date_joined'
        context['sort_direction'] = 'desc'
        if self.args and len(self.args) == 2:
            context['sort_field'] = self.args[0]
            context['sort_direction'] = self.args[1]
        return context


# Quick and dirty excel exports. Will later add a proper
# page in Comm Admin
class CategoriesReportView(CommunityMixin, ListView):
    report_output_name = "categories_report"

    def get_queryset(self):
        community = self.request.user.get_admin_community()
        queryset = CC3Profile.objects.filter(community=community,
                                             is_approved=True)
        return queryset

    def get_profile_categories(self, profile):
        return [cat.id for cat in profile.categories.all()]

    def dispatch(self, request, *args, **kwargs):
        processed_profiles = []
        categories = [
            {'id': cat.id, 'title': cat.get_title()}
            for cat in Category.objects.active()]
        category_counts = {}
        for category in categories:
            category_counts[category['title']] = 0

        for profile in self.get_queryset():
            profile_dict = SortedDict()
            profile_dict['business_name'] = profile.business_name
            profile_categories = self.get_profile_categories(profile)
            for category in categories:
                if category['id'] in profile_categories:
                    profile_dict[category['title']] = 1
                    category_counts[category['title']] += 1
                else:
                    profile_dict[category['title']] = ''
            processed_profiles.append(profile_dict)

        if not processed_profiles:
            processed_profiles = [[]]
            headings = None
        else:
            total_dict = SortedDict()
            total_dict['business_name'] = ugettext('Total')
            for category in categories:
                total_dict[category['title']] = \
                    category_counts[category['title']]
            processed_profiles.append(total_dict)
            headings = [ugettext('Business name')]
            headings.extend([cat['title'] for cat in categories])

        return ExcelResponse(
            processed_profiles, force_csv=True,
            output_name=self.report_output_name, header_override=headings)


class OfferCategoriesReportView(CategoriesReportView):
    report_output_name = "offer_categories_report"


class WantCategoriesReportView(CategoriesReportView):
    report_output_name = "want_categories_report"

    def get_profile_categories(self, profile):
        return [cat.id for cat in profile.want_categories.all()]


class TransactionListView(CommunityMixin, ListView):
    model = AdPaymentTransaction
    template_name = 'communityadmin/transactions.html'
    paginate_by = 10
    context_object_name = 'transactions'

    def get_queryset(self):
        community = self.request.user.get_admin_community()
        currency = getattr(settings, 'CYCLOS_CURRENCY_CODE', 'SN')
        transactions = backends.transactions(community=community.code,
                                             currency=currency,
                                             direction='desc')

        return transactions

    def get_context_data(self, **kwargs):
        context = super(TransactionListView, self).get_context_data(**kwargs)
        context['cyclos_base'] = '{0}/do/admin/viewTransaction'.format(
            settings.CYCLOS_FRONTEND_URL)

        return context

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
                raise Http404(_(
                    "Empty list and '%(class_name)s.allow_empty' is False.")
                    % {'class_name': self.__class__.__name__})
        context = self.get_context_data(object_list=self.object_list)
        if 'export' in request.POST and request.POST['export'] == u'export':
            export_transactions = self.object_list

            if len(export_transactions) == 0:
                export_transactions_p = [export_transactions]
            else:
                # massage the data
                export_transactions_p = self.process_export_transactions(
                    export_transactions)

            return ExcelResponse(export_transactions_p, force_csv=True,
                                 output_name="community_transactions")
        return self.render_to_response(context)

    def process_export_transactions(self, transactions):
        """
        Convert raw object list transactions into format as per template
        TODO would be neater to use same template for both HTML and CSV
        """
        processed_transactions = []

        for trans in transactions:
            amount = round(float(trans.amount), 2)
            amount = "%s%s" % (intcomma(int(amount)), ("%0.2f" % amount)[-3:])
            try:
                sender = trans.sender.get_profile().full_name
            except:
                try:
                    sender = trans.sender.cc3_profile.full_name
                except:
                    sender = trans.sender

            try:
                receiver = trans.recipient.get_profile().full_name
            except:
                try:
                    receiver = trans.recipient.cc3_profile.full_name
                except:
                    receiver = trans.recipient

            trans_dict = SortedDict()
            trans_dict["date"] = "%s %s" % (
                date_format(trans.created, use_l10n=True),
                time_format(trans.created, use_l10n=True)
            )
            trans_dict["from"] = sender
            trans_dict["to"] = receiver
            trans_dict["description"] = trans.description
            trans_dict["amount"] = "%s %s" % (amount, settings.CURRENCY_SYMBOL)

            processed_transactions.append(trans_dict)

        return processed_transactions


class WantsOffersListView(CommunityMixin, TemplateView):
    template_name = 'communityadmin/offers_wants.html'

    def get_context_data(self, **kwargs):
        context = super(WantsOffersListView, self).get_context_data(**kwargs)
        context['sbmenu'] = 'wants'

        form = kwargs['form']
        categories = []
        adtypes = []
        statuses = []

        if form.data:
            categories = form.data.getlist('category')
            adtypes = form.data.getlist('adtype')
            statuses = form.data.getlist('status')

        ad_list = Ad.objects.filter(created_by__community=context['community'])

        if categories:
            ad_list = ad_list.filter(category__in=categories)
        if adtypes:
            ad_list = ad_list.filter(adtype__in=adtypes)
        if statuses:
            ad_list = ad_list.filter(status__in=statuses)

        _filter = self.request.GET.get('q')
        if _filter:
            ad_list = ad_list.filter(
                Q(title__icontains=_filter) |
                Q(description__icontains=_filter) |
                Q(created_by__business_name__icontains=_filter) |
                Q(keywords__name__icontains=_filter))

        ad_list = ad_list.distinct()

        paginator = Paginator(ad_list, 10)
        page = self.request.GET.get('page')

        try:
            ads = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            ads = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results
            ads = paginator.page(paginator.num_pages)

        context['ads'] = ads

        # TODO: should use the paginator like in marketplace
        getvars = self.request.GET.copy()
        if 'page' in getvars:
            del getvars['page']
        if len(getvars.keys()) > 0:
            getvars = "&%s" % getvars.urlencode()
        else:
            getvars = ''

        context['getvars'] = getvars

        return context

    def get(self, request, *args, **kwargs):
        form = OffersWantsForm(data=self.request.GET)
        form.is_valid()

        context = self.get_context_data(form=form)
        return self.render_to_response(context)


@login_required
def update_profile(request, username,
                   template_name='communityadmin/edit_member.html'):
    try:
        cc3_profile = CC3Profile.viewable.get(user__username=username)
    except CC3Profile.DoesNotExist:
        # As long as the user isn't a superuser or community admin, create a
        # profile instance.
        user = User.objects.get(username=username)
        if user.is_superuser or user.get_admin_community():
            # TODO could raise a more explanatory exception here when time
            raise PermissionDenied

        app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
        model = models.get_model(app_label, model_name)
        cc3_profile = model.objects.create(user=user)
        log.addition(request, cc3_profile, message='Automatically created')

    if not request.user.is_superuser:
        admin_community = request.user.get_admin_community()
        if admin_community != cc3_profile.community:
            raise PermissionDenied

    # update it POST and data is valid
    if request.method == "POST":
        diff = log.Diff(cc3_profile)
        form = CC3ProfileForm(
            request.POST, request.FILES, instance=cc3_profile,
            user=request.user)

        if form.is_valid():
            cc3_profile = form.save()
            cc3_profile.update_slug()
            diff.log_if_changed(
                request,
                cc3_profile)

            messages.add_message(
                request, messages.INFO, _('Details saved successfully.'))
            if request.is_ajax():
                return_object = {'success': True}
                return HttpResponse(
                    json.dumps(return_object), content_type='appication/json')
            else:
                # must redirect
                return HttpResponseRedirect(
                    reverse('communityadmin_ns:editmember',
                            kwargs={'username': username}))
        else:
            if request.is_ajax():
                form.errors['__all__'] = ugettext(
                    'Unable to save your changes - Please enter all '
                    'required information and try again')
                data = json.dumps(form.errors)
                response_kwargs = {
                    'status': 400,
                    'content_type': 'application/json'
                }
                return HttpResponse(data, **response_kwargs)
            else:
                messages.add_message(
                    request, messages.WARNING, _('Please correct the form.'))

    else:
        form = None
        if cc3_profile:
            form = CC3ProfileForm(instance=cc3_profile, user=request.user)

    comms_url = ''
    limit_url = ''
    if cc3_profile:
        try:
            cyclos_id = cc3_profile.cyclos_account.cyclos_id
            comms_url = \
                settings.CYCLOS_FRONTEND_URL + '/do/admin/flatMemberRecords?' \
                                               'global=false&elementId=%s&' \
                                               'typeId=1' % cyclos_id
            limit_url = \
                settings.CYCLOS_FRONTEND_URL + '/do/admin/editCreditLimit?' \
                                               'memberId=%d' % cyclos_id
        except CyclosAccount.DoesNotExist:
            pass  # fall back to no urls

    return render_to_response(template_name, {
        'form': form,
        'cc3_profile': cc3_profile,
        'comms_url': comms_url,
        'limit_url': limit_url,
    }, context_instance=RequestContext(request))


class ProfileMixin(CommunityMixin):
    """
    Subclasses ``CommunityMixin``, so it performs the same security checks, and
    adds the ``CC3Profile`` instance of a given username to the view context.
    """
    def get_context_data(self, username, filter_individuals=False, **kwargs):
        context = super(ProfileMixin, self).get_context_data(**kwargs)
        cc3_profile = get_object_or_404(CC3Profile, user__username=username)

        context['cc3_profile'] = cc3_profile

        return context


class ChangePasswordView(ProfileMixin, TemplateView):
    template_name = 'communityadmin/change_password.html'

    subject_template_name = "communityadmin/new_password_subject.txt"
    email_template_name = "communityadmin/new_password_email.txt"

    def post(self, request, username):
        context = self.get_context_data(username=username)
        new_password = User.objects.make_random_password()
        cc3_profile = context['cc3_profile']
        user = cc3_profile.user

        user.set_password(new_password)
        user.save()
        cc3_profile.must_reset_password = True
        cc3_profile.save()

        new_password_message_dict = {
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'recipient_list': [user.email]
        }

        site = Site.objects.get_current()
        fullname = ' '.join(
            [user.cc3_profile.first_name, user.cc3_profile.last_name])

        new_password_message_dict['subject'] = loader.render_to_string(
            self.subject_template_name, {'site': site})
        new_password_message_dict['message'] = loader.render_to_string(
            self.email_template_name,
            {'name': fullname, 'site': site, 'password': new_password})

        send_mail(fail_silently=False, **new_password_message_dict)

        messages.add_message(request, messages.INFO, _('New password sent.'))

        return HttpResponseRedirect(
            reverse('communityadmin_ns:editmember', kwargs={
                'username': username}))


class ChangeGroupView(ProfileMixin, TemplateView):
    template_name = 'communityadmin/change_group.html'

    def get_groups_queryset(self):
        cc3_profile = CC3Profile.viewable.get(
            user__username=self.kwargs['username'])
        initial = list(cc3_profile.community.get_initial_groups().values_list(
            'id', flat=True))
        full = list(cc3_profile.community.get_full_groups().values_list(
            'id', flat=True))
        pks = initial + full

        return CyclosGroup.objects.filter(pk__in=pks)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        form = ChangeGroupForm()

        # Filter query to user's community's groups
        cc3_profile = context['cc3_profile']
        form.fields['groups'].queryset = self.get_groups_queryset()
        group_id = backends.get_group(cc3_profile.user.email)
        form.fields['groups'].initial = group_id

        context['form'] = form

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        form = ChangeGroupForm(request.POST)
        cc3_profile = context['cc3_profile']
        form.fields['groups'].queryset = self.get_groups_queryset()

        # Set original_group_id on form, for validation purposes.
        form.set_original_group_id(backends.get_group(cc3_profile.user.email))
        context['form'] = form

        if form.is_valid():
            cyclos_id = cc3_profile.cyclos_account.cyclos_id
            new_group_id = form.cleaned_data['groups'].id
            comments = form.cleaned_data['comments']
            backends.update_group(cyclos_id, new_group_id, comments)

            messages.add_message(request, messages.INFO, _('Group changed.'))
            return HttpResponseRedirect(
                reverse('communityadmin_ns:memberlist'))
        else:
            return self.render_to_response(context)


class MemberTransactionsView(ProfileMixin, AccountsView):
    template_name = 'communityadmin/membertransactions.html'

    def get_user(self):
        username = self.kwargs.get('username')
        user = User.objects.get(username=username)

        return user

    def get_context_data(self, **kwargs):
        context = super(MemberTransactionsView, self).get_context_data(**kwargs)
        if context['cc3_profile']:
            context['number_of_payments_made'] = \
                context['cc3_profile'].total_payments_outgoing()
            context['number_of_payments_received'] = \
                context['cc3_profile'].total_payments_incoming()

        try:
            cyclos_account = context['cc3_profile'].cyclos_account
            context['cyclos_id'] = cyclos_account.cyclos_id
        except:
            context['cyclos_id'] = None

        context['cyclos_base'] = '{0}/do/admin/viewTransaction'.format(
            settings.CYCLOS_FRONTEND_URL)

        return context


class MemberWantsOffersView(ProfileMixin, TemplateView):
    template_name = 'communityadmin/memberoffers_wants.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        """
        Overrides the ``dispatch`` method defined in ``CommunityMixin`` to
        perform an extra check on the requested user, filtering out those
        users who are individual and not business users or incomplete users
        who are not related yet to a groupset (then will get a 403 error).
        """
        cc3_profile = get_object_or_404(
            CC3Profile, user__username=kwargs['username'])

        try:
            if not cc3_profile.groupset.may_add_ads:
                raise PermissionDenied
        except AttributeError:
            raise PermissionDenied

        return super(
            MemberWantsOffersView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(MemberWantsOffersView, self).get_context_data(
            username=kwargs.get('username'), filter_individuals=True,
            form=kwargs.get('form'))

        form = kwargs['form']
        categories = []
        adtypes = []

        if form.data:
            categories = form.data.getlist('category')
            adtypes = form.data.getlist('adtype')

        ad_list = Ad.objects.filter(created_by=context['cc3_profile'])

        if categories:
            ad_list = ad_list.filter(category__in=categories)
        if adtypes:
            ad_list = ad_list.filter(adtype__in=adtypes)

        query = self.request.GET.get('q')
        if query:
            ad_list = ad_list.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(created_by__business_name__icontains=query) |
                Q(keywords__name__icontains=query)
            )

        ad_list = ad_list.distinct()

        paginator = Paginator(ad_list, 10)
        page = self.request.GET.get('page')

        try:
            ads = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            ads = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            ads = paginator.page(paginator.num_pages)

        context['ads'] = ads

        # TODO: should use the paginator like in marketplace
        getvars = self.request.GET.copy()
        if 'page' in getvars:
            del getvars['page']
        if len(getvars.keys()) > 0:
            getvars = "&%s" % getvars.urlencode()
        else:
            getvars = ''

        context['getvars'] = getvars

        return context

    def get(self, request, *args, **kwargs):
        form = OffersWantsForm(data=self.request.GET)
        form.is_valid()

        context = self.get_context_data(
            username=kwargs.get('username'), form=form)

        return self.render_to_response(context)


class AdCreate(CommunityMixin, CreateView):
    """ Community admin version of ad creation """
    template_name = 'communityadmin/place_ad.html'
    form_class = CommunityAdminAdForm
    model = Ad
    extra_context = None

    def get_success_url(self):
        return reverse('communityadmin_ns:wantsoffers')

    def dispatch(self, request, *args, **kwargs):
        # Upon GET delete all waiting PreAdImages
        if request.method == 'GET':
            PreAdImage.objects.filter(user_created=request.user).delete()

        return super(AdCreate, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        admin_community = request.user.get_admin_community()

        if admin_community is None:
            raise PermissionDenied
        form.set_community_id(admin_community.id)

        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.save()

            for img in PreAdImage.objects.filter(user_created=request.user):
                AdImage(
                    user_created=img.user_created, image=img.image,
                    caption=img.caption, height=img.height, width=img.width,
                    url=img.url, ad=self.object).save()
            return self.form_valid(form)

        return self.form_invalid(form)

    def render_to_json_response(self, context, formset=None, **response_kwargs):

        # formset only if there is a problem with the captions
        # so - alternative fix for now, as need to get site live
        # TODO: serialize formset errors for display in correct
        # place at front end
        if formset:
            data = u"%s%s%s" % (
                '{"captions": ["',
                _("Please make sure you have added captions for "
                  "all your images."),
                '"]}')
        else:
            data = json.dumps(context)

        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)

    def form_valid(self, form):
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, formset=None):
        super(AdCreate, self).form_invalid(form)
        if self.request.is_ajax():
            return self.render_to_json_response(
                form.errors, formset=formset, status=400)
        else:
            context = self.get_context_data()
            # use the formset if passed by validation route
            if formset:
                context['adimages_formset'] = formset
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(AdCreate, self).get_context_data(**kwargs)
        context['adimages_formset'] = AdImageFormSet()

        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value

        context.update({
            # TODO - move into parent to avoid duplication
            "browse": _("Browse..."),
            "add_image": _("Add Image"),
            "remove_image": _("Remove Image"),
            "sbmenu": 'place_ad',
        })
        return context


class CommunityAdUpdateView(CommunityMixin, MarketplaceAdUpdateView):
    """
    View to let the community admin update Ads created by himself or by the
    community members.
    """
    form_class = CommunityAdminAdUpdateForm
    model = Ad
    template_name = 'communityadmin/edit_ad.html'

    def get_success_url(self):
        return reverse('communityadmin_ns:wantsoffers')

    def get_context_data(self, **kwargs):
        """
        Add to the context the uploaded images related to this specific Ad.
        """
        context = super(CommunityAdUpdateView, self).get_context_data(**kwargs)
        context['ad_images'] = AdImage.objects.filter(ad=self.object)
        return context


class CommunityAdminAdDisableView(MarketplaceAdDisableView):
    """ Permission checked in MarketplaceAdDisable.dispatch """
    template_name = 'communityadmin/disable_ad.html'

    def get_success_url(self):
        return reverse('communityadmin_ns:wantsoffers')

    def get_context_data(self, **kwargs):
        context = super(CommunityAdminAdDisableView, self).get_context_data(
            **kwargs)
        context['sbmenu'] = 'suboffer'

        return context


class AdHold(UpdateView):
    model = Ad
    form_class = AdHoldForm
    extra_context = None
    template_name = 'communityadmin/hold_ad.html'

    def dispatch(self, request, *args, **kwargs):
        ad = self.get_object()
        if ad.can_edit(self.request.user):
            return super(AdHold, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_success_url(self):
        return reverse('communityadmin_ns:wantsoffers')

    def get_context_data(self, **kwargs):
        context = super(AdHold, self).get_context_data(**kwargs)

        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value
#        context['ad']

        return context


# AJAX info views
def created_by_auto(request):
    """
    Returns contact names for logged in user, if they are a community admin
    Returns data for the autocomplete field.

    Data is formatted as lines with three columns separated by tabs:
        1. completion data
        2. formatted data
        3. URL
    """
    admin_community = request.user.get_admin_community()
    if admin_community is None:
        raise PermissionDenied

    form = CommunityAdminCreatedByForm(request.GET)
    if form.is_valid():
        created_by_filter = form.cleaned_data['created_by_name']
        businesses = CC3Profile.viewable.filter(
            Q(business_name__icontains=created_by_filter) |
            Q(last_name__icontains=created_by_filter) |
            Q(first_name__icontains=created_by_filter)
        ).filter(
            community=admin_community
        ).exclude(user=request.user)

        business_names = businesses.distinct().order_by(
            'first_name', 'last_name').values_list(
                'id',
                'first_name',
                'last_name',
            )

        data = []
        for e in business_names:
            data.append({
                'id': e[0],
                'value': u'%s %s' % (e[1], e[2])
            })

        json_data = json.dumps(data)
        return HttpResponse(json_data, content_type='application.json')
    return HttpResponse('[]')


class CreateMemberWizard(CommunityMixin, SessionWizardView):
    file_storage = FileSystemStorage(
        location=os.path.join(settings.MEDIA_ROOT, 'comm_admin_temp'))

    def get_context_data(self, form, **kwargs):
        context = super(CreateMemberWizard, self).get_context_data(
            form=form, **kwargs)

        # Add community code if step 1 (registration)
        if self.steps.current == "0":
            try:
                community_code = CommunityRegistrationCode.objects.filter(
                    community=context['community'])[0]
                context['community_code'] = community_code.code
            except CommunityRegistrationCode.DoesNotExist:
                context['community_code'] = ""
            except IndexError:
                context['community_code'] = ""

        context['sbmenu'] = 'addmember'
        return context

    def get_template_names(self):
        return ['communityadmin/create_member_wizard_{0}.html'.format(
            self.steps.current)]

    def done(self, form_list, **kwargs):
        # Do all user and profile creation here, as if done before, the forms
        # invalidate themselves.

        registration_form = form_list[0]
        cc3_profile_form = form_list[1]

        # Code from django registration - copied and updated for speed.
        # Needs refactoring.
        community_code = registration_form.cleaned_data['community_code']
        if community_code and community_code.strip() != '':
            cc3_community = CC3Community.objects.get(
                communityregistrationcode__code=community_code)
        else:
            cc3_community = CC3Community.objects.get(
                pk=settings.DEFAULT_COMMUNITY_ID)

        from cc3.accounts.utils import get_non_obvious_number

        # get unused username (never shown to users)
        email = registration_form.cleaned_data['email']

        # max length of username on cyclos side is 30 chars
        # user won't ever know their generated username
        username = slugify(email[:30])
        username = "".join(
            [ch for ch in username if ch in (ascii_letters + digits)])

        # check username doesn't already exist (on django side)
        test_username = username.ljust(4, '0')
        while True:
            list_of_members_with_username = User.objects.filter(
                username=test_username)
            if len(list_of_members_with_username) == 0:
                break
            test_username = "{0}{1}".format(
                username, get_non_obvious_number(number_digits=4))

        username = test_username

        email = registration_form.cleaned_data['email']
        password = registration_form.cleaned_data['password_confirmation']
        activate_immediately = registration_form.cleaned_data.get(
            'activate_immediately', False)
        site = Site.objects.get_current()

        # Important difference - this *does not* send the activation email.
        # This only happens when the registration is complete. May need a way
        # to send this activation email via the Django admin interface in case
        # of failures.
        new_user = RegistrationProfile.objects.create_inactive_user(
            username, email, password, site, send_email=False)
        new_user = User.objects.get(pk=new_user.pk)

        cc3_profile = CC3Profile.objects.create(
            user=new_user,
            first_name=cc3_profile_form.cleaned_data['first_name'],
            last_name=cc3_profile_form.cleaned_data['last_name'],
            business_name=cc3_profile_form.cleaned_data['business_name'],
            community=cc3_community,
            country=cc3_community.country,
            picture=cc3_profile_form.cleaned_data['picture'],
            job_title=cc3_profile_form.cleaned_data['job_title'],
            city=cc3_profile_form.cleaned_data['city'],
            address=cc3_profile_form.cleaned_data['address'],
            postal_code=cc3_profile_form.cleaned_data['postal_code'],
            #registration_number=cc3_profile_form.cleaned_data[
            #    'registration_number'],
            phone_number=cc3_profile_form.cleaned_data['phone_number'],
            mobile_number=cc3_profile_form.cleaned_data['mobile_number'],
            company_website=cc3_profile_form.cleaned_data['company_website'],
            company_description=cc3_profile_form.cleaned_data[
                'company_description'],
        )
        cc3_profile.update_slug()

        # send the activation email, or activate the user
        registration_profile = RegistrationProfile.objects.get(user=new_user)
        if activate_immediately:
            registration_profile.activation_key = RegistrationProfile.ACTIVATED
            registration_profile.save()
            new_user.is_active = True
            new_user.save()
        else:
            site = Site.objects.get_current()
            registration_profile.send_activation_email(site)

        # add message saying user X was created
        messages.add_message(
            self.request, messages.INFO, _('New Member created successfully.'))

        # redirect to member list (which will show message)
        return HttpResponseRedirect(reverse('communityadmin_ns:memberlist'))


# Create view function from CreateMemberWizard with forms provided.
create_member_wizard = CreateMemberWizard.as_view([
    TradeQoinRegistrationForm, CC3ProfileForm])


def categories_auto(request):
    """
    Returns category IDs for a specified user, if they are a community admin,
    and the user is in their community.
    """
    form = CommunityAdminCategoriesForm(request.GET)
    # check GET profile_id is valid - ie an integer
    if form.is_valid():
        profile_id = form.cleaned_data['profile_id']
        # if this isnt' the owner of the data, check it's a comm admin
        cc3_profile = CC3Profile.viewable.get(pk=profile_id)

        request_cc3_profile = None
        try:
            request_cc3_profile = CC3Profile.viewable.get(user=request.user)
        except CC3Profile.DoesNotExist:
            pass

        if not (request_cc3_profile == cc3_profile):
            admin_community = request.user.get_admin_community()
            if admin_community is None:
                raise PermissionDenied

            # if comm admin, check it's the right community
            if cc3_profile.community != admin_community:
                raise PermissionDenied

        # optional ad_code can be used to request want_categories instead
        # of the default (offer) categories
        ad_code = form.cleaned_data.get('ad_code', '')
        if ad_code in ('W', 'w'):
            cat_queryset = cc3_profile.want_categories.all()
        else:
            cat_queryset = cc3_profile.categories.all()

        categories = cat_queryset.values_list('id', flat=True)

        data = []
        for e in categories:
            data.append({
                'id': e,
            })
        data.sort()

        json_data = json.dumps(data)
        return HttpResponse(json_data, content_type='application.json')

    return HttpResponse('[]')
