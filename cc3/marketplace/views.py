import datetime
from decimal import Decimal
import json
import logging
import operator
import re
import string
from functools import reduce

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.core.exceptions import (
    ValidationError, FieldError, ObjectDoesNotExist)
from django.db import models
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.shortcuts import get_object_or_404, render_to_response, render
from django.template.context import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (CreateView, DetailView, ListView,
                                  UpdateView)
from django.views.generic.base import ContextMixin

from cc3.accounts.decorators import must_have_completed_profile
from cc3.cyclos.common import TransactionException
from cc3.cyclos.forms import CC3ProfileDisplayForm
from cc3.cyclos.models import CC3Profile, CC3Community, CyclosGroup
from cc3.cyclos import backends

from .common import AD_STATUS_ACTIVE, AD_STATUS_ONHOLD
from .forms import (
    AdForm, MarketplaceForm, MarketplacePayForm,
    WantContactForm, MarketplaceSearchForm, AdDisableForm,
    AdToggleStatusForm, BusinessFilterForm,
    CampaignForm, CampaignFilterForm, CampaignSignupForm,
    CancelCampaignForm, RemoveCampaignParticipantForm,
    RewardCampaignParticipantForm
    )
from .models import (
    Ad, AdImage, AdType, AdPaymentTransaction, PreAdImage,
    Campaign, CampaignParticipant,
    CAMPAIGN_STATUS_VISIBLE, CAMPAIGN_STATUS_CANCELLED,
    CAMPAIGN_STATUS_HIDDEN
    )
from .utils import (
    QuerySetChain, user_can_join_campaigns, user_can_own_campaigns)

from cc3.cyclos.utils import is_consumer_member

tokenize_regex = re.compile(r'[%s\s]+' % re.escape(string.punctuation))

LOG = logging.getLogger(__name__)


class MarketplaceAdCreateView(CreateView):
    form_class = AdForm
    model = Ad
    extra_context = None
    template_name = 'accounts/place_ad.html'

    def __init__(self, *args, **kwargs):
        self.object = None
        super(MarketplaceAdCreateView, self).__init__()

    def dispatch(self, request, *args, **kwargs):
        """
        Check to ensure 'may_add_ads' has been set for this user's GroupSet.
        """
        cc3_profile = request.user.get_cc3_profile()
        if cc3_profile and not cc3_profile.groupset.may_add_ads:
            raise Http404

        # Prepopulate the categories based on the categories set on the profile
        self.initial = {'category': cc3_profile.categories.all().values_list(
            'id', flat=True)}

        # Upon GET delete all waiting PreAdImages
        if request.method == 'GET':
            PreAdImage.objects.filter(user_created=request.user).delete()

        return super(MarketplaceAdCreateView, self).dispatch(
            request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        if using separate offer and want categories, form needs to update them
        so add flag to context
        """
        context = super(MarketplaceAdCreateView, self).get_context_data(
            **kwargs)
        if getattr(settings, 'WANT_CATEGORIES_IN_PROFILE', False):
            try:
                context['want_categories_adtype'] = \
                    AdType.objects.get(code='W').pk
            except AdType.DoesNotExist:
                pass
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.created_by = request.user.get_profile()
            if getattr(settings, 'MARKETPLACE_ADS_NEED_APPROVAL', False):
                self.object.status = AD_STATUS_ONHOLD
                messages.add_message(request, messages.INFO, _(
                    u'Your ad will be visible once an administrator has '
                    u'approved it'))
            else:
                self.object.status = AD_STATUS_ACTIVE
            self.object.save()
            form.save_m2m()
            for img in PreAdImage.objects.filter(user_created=request.user):
                AdImage(user_created=img.user_created, image=img.image,
                        caption=img.caption, height=img.height,
                        width=img.width, url=img.url, ad=self.object).save()
            return self.form_valid(form)

        return self.form_invalid(form)

    def render_to_json_response(self, context, formset=None, **response_kwargs):
        # TODO: To be reviewed... and probably moved. Deprecated formset stuff.
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
        if self.request.is_ajax():
            return_object = {'success': True}
            return HttpResponse(
                json.dumps(return_object), content_type='application/json')
        else:
            # must redirect
            return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.is_ajax():
            return self.render_to_json_response(form.errors, status=400)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class AdEditionMixin(object):
    """
    Mixin object to generalize permissions over the Ads edition views.
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Overrides base class ``dispatch`` method to check if the request user
        is allowed to edit the selected Ad.

        Login requirement and extra permissions are enforced in the URLs file.
        """
        ad = self.get_object()
        if ad.can_edit(self.request.user):
            return super(AdEditionMixin, self).dispatch(
                request, *args, **kwargs)
        else:
            raise PermissionDenied


class MarketplaceAdUpdateView(AdEditionMixin, UpdateView):
    model = Ad
    form_class = AdForm
    template_name = 'marketplace/edit_ad.html'

    def get_success_url(self):
        return reverse('accounts_my_ads')

    def get_context_data(self, **kwargs):
        """
        Add to the context the uploaded images related to this specific Ad.
        """
        context = super(MarketplaceAdUpdateView, self).get_context_data(
            **kwargs)
        context['ad_images'] = AdImage.objects.filter(ad=self.object)
        context['sbmenu'] = 'editad'
        return context

    def form_valid(self, form):
        is_admin = (self.request.user.is_superuser or
                    self.request.user.is_community_admin())
        if not is_admin and getattr(
                settings, 'MARKETPLACE_ADS_NEED_APPROVAL', False):
            form.instance.status = AD_STATUS_ONHOLD
            messages.add_message(self.request, messages.INFO, _(
                u'Your ad will be visible once an administrator '
                u'has approved it'))
        form.save()
        if self.request.is_ajax():
            return_object = {'success': True}
            return HttpResponse(
                json.dumps(return_object), content_type='application/json')
        else:
            # must redirect
            return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        super(MarketplaceAdUpdateView, self).form_invalid(form)
        if self.request.is_ajax():
            return self.render_to_json_response(form.errors, status=400)
        else:
            context = self.get_context_data()
            return self.render_to_response(context)

    def render_to_json_response(self, context, formset=None, **response_kwargs):
        # TODO: To be reviewed... and probably moved. Deprecated formset stuff.
        if formset:
            data = u"%s%s%s" % (
                '{"captions": ["',
                _("Please make sure you have added captions for all your "
                  "images."),
                '"]}')
        else:
            data = json.dumps(context)

        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)


class MarketplaceAdToggleStatusView(UpdateView):
    model = Ad
    form_class = AdToggleStatusForm
    template_name = 'accounts/toggle_ad_status.html'

    def dispatch(self, request, *args, **kwargs):
        ad = self.get_object()
        if ad.can_edit(self.request.user):
            return super(MarketplaceAdToggleStatusView, self).dispatch(
                request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_success_url(self):
        return reverse('accounts_my_ads')


class MarketplaceAdDisableView(UpdateView):
    model = Ad
    form_class = AdDisableForm
    extra_context = None
    template_name = 'accounts/disable_ad.html'

    def dispatch(self, request, *args, **kwargs):
        ad = self.get_object()
        if ad.can_edit(self.request.user):
            return super(MarketplaceAdDisableView, self).dispatch(
                request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_success_url(self):
        return reverse('accounts_my_ads')

    def get_context_data(self, **kwargs):
        context = super(MarketplaceAdDisableView, self).get_context_data(
            **kwargs)

        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value

        return context


class AdDetail(DetailView):
    model = Ad

    def dispatch(self, request, *args, **kwargs):
        ad = self.get_object()
        if ad.can_view(self.request.user):
            return super(AdDetail, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super(AdDetail, self).get_context_data(**kwargs)

        if context['view'].request.user != context['object'].created_by.user:
            views = context['object'].views
            context['object'].views = views + 1
            context['object'].save()

        # add a warning message if the Ad is currently On Hold
        if context['object'].status == AD_STATUS_ONHOLD:
            messages.add_message(self.request, messages.INFO, _(
                u'Preview only: This ad will not be visible to other users '
                u'until approved by the administrator'))

        return context


class AdListView(ListView):
    """ for my-ads """
    model = Ad
    context_object_name = 'ad_list'
    extra_context = None
    paginate_by = 10
    template_name = 'accounts/my_ads.html'

    def get_queryset(self):
        # sorting / ordering
        field = 'title'
        direction = 'asc'
        if self.args and len(self.args) == 2:
            field = self.args[0]
            direction = self.args[1]
        order_by_direction = ''
        if direction == 'desc':
            order_by_direction = '-'

        order_by = u'{0}{1}'.format(order_by_direction, field)
        try:
            return Ad.objects.filter(
                created_by=self.request.user.cc3_profile).order_by(order_by)
        except FieldError:
            return Ad.objects.filter(created_by=self.request.user.cc3_profile)

    def get_context_data(self, **kwargs):
        context = super(AdListView, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value

        # The admin details, used in the onhold-popup
        admin = self.request.user.get_community_admin()
        if admin:
            context['admin_name'] = ' '.join([admin.first_name,
                                              admin.last_name])
            context['admin_email'] = admin.email

        # DRY violated...
        context['myads_field'] = 'title'
        context['myads_direction'] = 'asc'
        if self.args and len(self.args) == 2:
            context['myads_field'] = self.args[0]
            context['myads_direction'] = self.args[1]
        return context


class CommunityNoFilterMixin(ContextMixin):
    """
    Mixin class to add the ``not_all_communities_no_filter``
    context variable to the marketplace views.
    """
    def get_context_data(self, **kwargs):
        """
        Adds not_all_communities_no_filter if user is anonymous.
        This checks whether all communties communtiy_view is set to
        'no_filter' and if so, sets not_all_communities_no_filter to true
        so that marketplace community filter menu can be hidden
        """
        context = super(CommunityNoFilterMixin, self).get_context_data(**kwargs)

        no_filters = None

        # do nothing if authenticated user (as they will have a
        # community that will determine this)
        if not self.request.user.is_authenticated():
            communities_no_filters = CC3Community.objects.exclude(
                community_view=CC3Community.NO_FILTER)
            no_filters = communities_no_filters.count()

        context['not_all_communities_no_filter'] = no_filters

        return context


class BusinessView(CommunityNoFilterMixin, ListView):
    paginate_by = 12
    queryset = CC3Profile.viewable.all()
    extra_context = None
    search_term = None
    template_name = 'marketplace/ad_list.html'
    form_class = BusinessFilterForm
    start_tab = u'businesses'
    require_location = False

    def __init__(self, *args, **kwargs):
        self.object_list = None
        super(BusinessView, self).__init__(*args, **kwargs)

    # Following functions are pulled out so that sites can
    # override as needed
    def apply_categories_filter(self, businesses, categories):
        children = []
        for category in categories:
            children += list(category.children.all())
        return businesses.filter(Q(categories__in=categories) |
                                 Q(categories__in=children))

    def apply_profile_type_filter(self, businesses, profile_types):
        """
        :param businesses: businesses to filter
        :param profile_types: which profile types to show
        :return: filtered businesses
        """

        # Core CC3 does not have different profile types, so return the
        # 'businesses' passed to method
        return businesses

    def get_adtype(self):
        # use adtype in GET if necessary
        get_adtype = self.request.GET.get('adtype', None)
        if get_adtype:
            adtype = [AdType.objects.get(pk=get_adtype[0:1]).pk]
        else:
            adtype = self.request.session.get('marketplace_adtype', None)
        return adtype

    def get_initial_businesses(self):
        return CC3Profile.viewable.filter(
            models.Q(
                is_visible=True,
                groupset__is_visible=True) |
            models.Q(
                is_visible=True,
                cyclos_group__visible_to_all_communities=True
            )
        )

    def get_paginate_by(self, queryset):
        """
        Paginate by value saved to session, or use default class property value.
        """
        return self.request.session.get(
            'marketplace_paginate_by', self.paginate_by)

    def get_businesses(self, businesses, categories, community, adtype,
                       profile_types):
        """
        Given a queryset of businesses, apply the selected categories,
        community and adtype filters from the marketplace-filter form.

        Returns a tuple of sorted business dictionaries, containing the
        business name, number of offers, number of wants and a reference
        to the CC3Profile for the business.

        Note that the sorting of the businesses depends on
        settings.MARKETPLACE_SORT_MY_COMMUNITY_FIRST
        """
        from operator import itemgetter

        unsorted_my_community_businesses = []
        unsorted_businesses = []
        users_checked = []

        # get users profile and community early on (if authenticated),
        # rather than in loop that looks at every business (see later in view)
        my_cc3_profile = my_cc3_profile_community = None
        if self.request.user.is_authenticated() and \
                not self.request.user.is_superuser:
            try:
                my_cc3_profile = self.request.user.cc3_profile
                my_cc3_profile_community = my_cc3_profile.community
            except CC3Profile.DoesNotExist:
                pass

        # Show all businesses with the selected category or any sub-category
        # below the selected category
        if categories:
            businesses = self.apply_categories_filter(businesses, categories)

        if profile_types:
            businesses = self.apply_profile_type_filter(businesses,
                                                        profile_types)
        if community:
            businesses = businesses.filter(community__id__in=community)
        else:
            # filter by community depending on the community admin preferences
            # deal with MEMBERS_ONLY here (MEMBERS_FIRST is done later)
            if my_cc3_profile and my_cc3_profile_community.community_view == \
                            CC3Community.MEMBERS_ONLY:
                businesses = businesses.filter(
                    models.Q(
                        community=my_cc3_profile_community
                    ) | models.Q(
                        cyclos_group__visible_to_all_communities=True
                    )
                )

        if adtype:
            businesses = businesses.filter(ad__adtype__in=adtype)

        if self.search_term:
            businesses = businesses.filter(
                models.Q(business_name__icontains=self.search_term)
            ).distinct()
            or_queries = []
            for bit in tokenize_regex.split(self.search_term.strip()):
                or_queries += [
                    models.Q(business_name__icontains=bit) |
                    models.Q(ad__title__icontains=bit)
                ]
            businesses = businesses.filter(reduce(operator.or_, or_queries))

        if self.require_location:
            businesses = businesses.filter(
                latitude__isnull=False, longitude__isnull=False)

        businesses = businesses.distinct()

        # determine whether to show businesses in the users community first
        # depending on settings (and community_view setting)
        my_community_first = settings.MARKETPLACE_SORT_MY_COMMUNITY_FIRST and \
            self.request.user.is_authenticated()
        if my_cc3_profile_community and \
            my_cc3_profile_community.community_view == \
                CC3Community.MEMBERS_FIRST:
            my_community_first = True

        # collect info on a businesses adverts, and arrange by community
        # (if community_view setting makes this necessary)
        for cc3_profile in businesses:
            if cc3_profile and cc3_profile.id and cc3_profile.id not in \
                    users_checked:
                if cc3_profile.business_name != '' and cc3_profile.slug != '':
                    business = {
                        'business_name': cc3_profile.business_name,
                        'offers': Ad.objects.filter(
                            created_by=cc3_profile,
                            adtype__code__iexact='o',
                            status=AD_STATUS_ACTIVE).count(),
                        'wants': Ad.objects.filter(
                            created_by=cc3_profile,
                            adtype__code__iexact='w',
                            status=AD_STATUS_ACTIVE).count(),
                        'cc3_profile': cc3_profile,
                        'group_name':
                            cc3_profile.cyclos_group and
                            cc3_profile.cyclos_group.name or ''
                    }

                    if my_community_first and my_cc3_profile and \
                            my_cc3_profile_community == cc3_profile.community:
                        unsorted_my_community_businesses.append(business)
                    else:
                        unsorted_businesses.append(business)
                if cc3_profile:
                    users_checked.append(cc3_profile.id)

        # recombine lists and sort by business name
        businesses = (
            sorted(unsorted_my_community_businesses,
                   key=itemgetter('business_name')) +
            sorted(unsorted_businesses, key=itemgetter('business_name'))
        )

        if getattr(
                settings, "MARKETPLACE_INDIVIDUALS_HIDE_IF_NO_ADVERTS", False):

            customer_member_groups = getattr(
                        settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', [])
            reduced_businesses = []
            for business in businesses:
                if business['group_name'] in customer_member_groups:
                    if business['offers'] != 0 or business['wants'] != 0:
                        reduced_businesses.append(business)
                else:
                    reduced_businesses.append(business)
            businesses = reduced_businesses

        return businesses

    def get(self, request, *args, **kwargs):
        search_form = MarketplaceSearchForm(request.GET)
        self.search_term = None
        if search_form.is_valid():
            self.search_term = search_form.cleaned_data['search']
            self.request.session['search_term'] = self.search_term
        elif 'search' in self.request.GET:
            self.search_term = None
            if 'search_term' in self.request.session:
                del request.session['search_term']
            request.session.modified = True
        elif 'search_term' in self.request.session:
            self.search_term = self.request.session['search_term']

        if request.method == 'GET':
            if request.user.is_authenticated() and \
                            request.GET.get('csrfmiddlewaretoken',
                                            None) is None:

                cc3_profile = request.user.get_cc3_profile()

                if cc3_profile:
                    form_data = {
                        'community': [cc3_profile.community.id]
                    }
                else:
                    form_data = {}

                form_data.update(request.GET)
            else:
                form_data = request.GET

            form = self.form_class(form_data, user=request.user)

            # set some kwargs for the query set filtering
            if form.is_valid():
                if 'paginate_by' in form.cleaned_data:
                    self.request.session['marketplace_paginate_by'] = \
                        form.cleaned_data['paginate_by']
                paginate_by = self.request.session.get(
                    'marketplace_paginate_by', self.paginate_by)

                self.request.session['marketplace_sort_by'] = \
                    form.cleaned_data['sort_by']
                self.request.session['marketplace_adtype'] = \
                    form.cleaned_data.get('adtype', None)
                # in case form has been customised, and does not include
                # categories
                if 'categories' in form.cleaned_data:
                    self.request.session['marketplace_categories'] = \
                        form.cleaned_data['categories']
                # profile types not available in all CC3 projects
                if 'profile_types' in form.cleaned_data:
                    self.request.session['marketplace_profile_types'] = \
                        form.cleaned_data['profile_types']
                self.request.session['marketplace_community'] = \
                    form.cleaned_data.get('community', None)
                self.request.session['marketplace_from_price'] = \
                    form.cleaned_data['from_price']
                self.request.session['marketplace_to_price'] = \
                    form.cleaned_data['to_price']
            else:
                # If no paginate_by supplied, use the view default -- otherwise
                # switching between map and list view is problematic
                self.request.session['marketplace_paginate_by'] = \
                    self.paginate_by
                paginate_by = self.paginate_by
        else:
            # catch non standard requests (ie bots HEAD)
            paginate_by = self.paginate_by

        sort_by = self.request.session.get('marketplace_sort_by', None)
        adtype = self.get_adtype()
        categories = self.request.session.get('marketplace_categories', None)
        self.request.session['marketplace_adtype'] = adtype
        community = self.request.session.get('marketplace_community', None)
        from_price = self.request.session.get('marketplace_from_price', None)
        to_price = self.request.session.get('marketplace_to_price', None)
        profile_types = self.request.session.get('marketplace_profile_types',
                                                 None)

        if self.paginate_by or sort_by or adtype or categories or community or \
                from_price or to_price:
            form_data = {
                'paginate_by': paginate_by,
                'sort_by': sort_by,
                'adtype': adtype,
                'categories': categories,
                'community': community,
                'from_price': from_price,
                'to_price': to_price,
                'profile_types': profile_types
                }

            form = self.form_class(form_data, user=request.user)
        else:
            form = self.form_class(user=request.user)

        visible_businesses = self.get_initial_businesses()
        self.object_list = self.get_businesses(
            visible_businesses, categories, community, adtype, profile_types)
        context = self.get_context_data(object_list=self.object_list)

        # inject validated form and filters
        context['search_term'] = self.search_term
        context['marketplace_form'] = form
        context['start_tab'] = self.start_tab

        context['business_list'] = self.object_list
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BusinessView, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value
        return context


class BusinessMapView(BusinessView):
    start_tab = "businesses_map"
    # ad_list includes the marketplace/businesses_map_page.html,
    # as the BusinessView includes the marketplace/business_page.html
    # This view does not need the template_name overwritten. Especially
    # if replacing without testing at the front end!
#    template_name = 'marketplace/businesses_map_page.html'
    paginate_by = 2000
    require_location = True

    def get_context_data(self, **kwargs):
        context = super(BusinessView, self).get_context_data(**kwargs)

        # default map center north pole or there abouts
        context['map_centre_lat'] = getattr(
            settings, 'MARKETPLACE_MAP_CENTER_LAT', 0)
        context['map_centre_lng'] = getattr(
            settings, 'MARKETPLACE_MAP_CENTER_LNG', 0)
        context['search_on_map'] = True
        return context


class MarketplaceView(CommunityNoFilterMixin, ListView):
    paginate_by = getattr(settings, 'MARKETPLACE_PAGINATION_BY', 12)
    model = Ad
    extra_context = None
    search_term = None
    template_name = 'marketplace/ad_list.html'
    form_class = MarketplaceForm

    def get_paginate_by(self, queryset):
        """
        Paginate by value saved to session, or use default class property value.
        """
        return self.request.session.get(
            'marketplace_paginate_by', self.paginate_by)

    def apply_profile_type_filter(self, queryset, profile_types):
        """
        :param queryset: queryset to filter
        :param profile_types: which profile types to show
        :return: filtered queryset
        """

        # Core CC3 does not have different profile types, so return the
        # 'businesses' passed to method
        return queryset

    def get_queryset(self, business_slug=None, offers_wants=None):

        # save last POST to session for use in sorted / ordered view
        sort_by = self.request.session.get('marketplace_sort_by', None)
        categories = self.request.session.get('marketplace_categories', None)
        adtype = self.request.session.get('marketplace_adtype', None)
        community = self.request.session.get('marketplace_community', None)
        from_price = self.request.session.get('marketplace_from_price', None)
        to_price = self.request.session.get('marketplace_to_price', None)
        profile_types = self.request.session.get(
            'marketplace_profile_types', None)

        queryset = super(MarketplaceView, self).get_queryset()

        if categories:
            children = []
            for category in categories:
                children += list(category.children.all())
            queryset = queryset.filter(Q(category__in=categories) |
                                       Q(category__in=children))
        if adtype:
            queryset = queryset.filter(adtype__in=adtype)
        if to_price:
            queryset = queryset.filter(price__lte=to_price)
        if from_price:
            queryset = queryset.filter(price__gte=from_price)
        if profile_types:
            queryset = self.apply_profile_type_filter(queryset, profile_types)

        if self.search_term:
            for bit in tokenize_regex.split(self.search_term.strip()):
                or_queries = [
                    models.Q(title__icontains=bit) |
                    models.Q(created_by__business_name__icontains=bit) |
                    models.Q(keywords__name=bit)
                ]
                queryset = queryset.filter(reduce(operator.or_, or_queries))

            queryset = queryset.distinct()

        if business_slug:
            queryset = queryset.filter(
                created_by__slug=business_slug
            )
            if offers_wants == u'offers':
                queryset = queryset.filter(
                    adtype__code__iexact='o'
                )
            else:
                queryset = queryset.filter(
                    adtype__code__iexact='w'
                )

        # only ever show active ads in marketplace
        queryset = queryset.filter(status=AD_STATUS_ACTIVE)

        # sorting / ordering
        def _order_by_str(field, _dir):
            return u"{}{}".format(
                "" if _dir == "asc" else "-", field)

        # Requirements are odd/not straight forward:
        # https://support.community-currency.org/ticket/1494
        if sort_by:
            sort_field, sort_dir = sort_by.split('__')
            if sort_field == 'price':
                order_bys = (_order_by_str('price', sort_dir),
                             _order_by_str('date_created', 'desc'))
            else:
                order_bys = (_order_by_str(sort_field, sort_dir),)
        else:
            order_bys = (_order_by_str('date_created', 'desc'),)

        queryset_chain_used = False

        if community:
            # specific community list
            queryset = queryset.filter(created_by__community__in=community)
        else:
            # filter by community depending on the community admin preferences
            user = self.request.user
            if user.is_authenticated() and not user.is_superuser:
                try:
                    cc3_profile = self.request.user.cc3_profile

                    if cc3_profile.community.community_view == \
                            CC3Community.MEMBERS_FIRST:
                        queryset = QuerySetChain(
                            queryset.filter(
                                created_by__community=cc3_profile.community,
                                created_by__is_visible=True).order_by(*order_bys),
                            queryset.exclude(
                                created_by__community=cc3_profile.community,
                                created_by__is_visible=True).order_by(*order_bys)
                        )
                        queryset_chain_used = True
                    elif cc3_profile.community.community_view == \
                            CC3Community.MEMBERS_ONLY:
                        queryset = queryset.filter(models.Q(
                            created_by__community=cc3_profile.community
                        ) | models.Q(
                            created_by__cyclos_group__visible_to_all_communities=True
                        )).order_by(*order_bys)

                    return queryset
                except CC3Profile.DoesNotExist:
                    pass

        if not queryset_chain_used:
            # only show ads from profiles which are visible
            queryset = queryset.filter(created_by__is_visible=True)
            # order queryset
            queryset = queryset.order_by(*order_bys)

        return queryset.distinct()

    def get(self, request, *args, **kwargs):
        start_tab = u'products_and_services'
        business_slug = offers_wants = categories = community = adtype = None

        if self.args and len(self.args) > 0:
            if self.args[0] == u'offers' or self.args[0] == u'wants':
                offers_wants = self.args[0]
                business_slug = self.args[1]

        # reset form on GET (only when first access, not when paginating!)
        if not self.request.GET.get('page'):
            if not start_tab == 'businesses':
                self.request.session.pop('marketplace_paginate_by', None)

                self.request.session.pop('marketplace_sort_by', None)
                self.request.session.pop('marketplace_adtype', None)
                self.request.session.pop('marketplace_categories', None)
                self.request.session.pop('marketplace_community', None)
                self.request.session.pop('marketplace_from_price', None)
                self.request.session.pop('marketplace_to_price', None)
                self.request.session.pop('marketplace_profile_types', None)

        if offers_wants:
            form = None
        else:
            search_form = MarketplaceSearchForm(request.GET)
            self.search_term = None
            if search_form.is_valid():
                self.search_term = search_form.cleaned_data['search']
                self.request.session['search_term'] = self.search_term
            elif 'search' in self.request.GET:
                self.search_term = None
                if 'search_term' in self.request.session:
                    del request.session['search_term']
                    request.session.modified = True
            elif 'search_term' in self.request.session:
                self.search_term = self.request.session['search_term']

            if request.method == 'GET':
                if request.user.is_authenticated() and \
                                request.GET.get('csrfmiddlewaretoken',
                                                None) is None:
                    cc3_profile = request.user.get_cc3_profile()

                    if cc3_profile:
                        form_data = {
                            'community': [cc3_profile.community.id]
                        }
                    else:
                        form_data = {}

                    form_data.update(request.GET)
                else:
                    form_data = request.GET

                form = self.form_class(form_data, user=request.user)
                # set some kwargs for the query set filtering
                if form.is_valid():
                    if 'paginate_by' in form.cleaned_data:
                        self.request.session['marketplace_paginate_by'] = \
                            form.cleaned_data['paginate_by']
                    self.request.session['marketplace_sort_by'] = \
                        form.cleaned_data['sort_by']
                    self.request.session['marketplace_adtype'] = \
                        form.cleaned_data['adtype']

                    self.request.session['marketplace_categories'] = \
                        form.cleaned_data['categories']
                    self.request.session['marketplace_community'] = \
                        form.cleaned_data['community'] or None
                    self.request.session['marketplace_from_price'] = \
                        form.cleaned_data['from_price']
                    self.request.session['marketplace_to_price'] = \
                        form.cleaned_data['to_price']
                    if 'profile_types' in form.cleaned_data:
                        self.request.session['marketplace_profile_types'] = \
                            form.cleaned_data['profile_types']

            else:
                paginate_by = self.request.session.get(
                    'marketplace_paginate_by', None)
                sort_by = self.request.session.get('marketplace_sort_by', None)
                # use adtype in GET if necessary
                get_adtype = self.request.GET.get('adtype', None)
                if get_adtype:
                    try:
                        adtype = [AdType.objects.get(pk=get_adtype[0:1]).pk]
                    # catch bot HEAD error
                    except ValueError:
                        adtype = AdType.objects.all()[0]
                else:
                    adtype = self.request.session.get(
                        'marketplace_adtype', None)
                categories = self.request.session.get(
                    'marketplace_categories', None)
                self.request.session['marketplace_adtype'] = adtype
                community = self.request.session.get(
                    'marketplace_community', None)
                from_price = self.request.session.get(
                    'marketplace_from_price', None)
                to_price = self.request.session.get(
                    'marketplace_to_price', None)
                profile_types = self.request.session.get(
                    'marketplace_profile_types', None)

                if paginate_by or sort_by or adtype or categories or community \
                        or from_price or to_price or profile_types:
                    form_data = {
                        'paginate_by': paginate_by,
                        'sort_by': sort_by,
                        'adtype': adtype,
                        'categories': categories,
                        'community': community,
                        'from_price': from_price,
                        'to_price': to_price,
                        'profile_types': profile_types
                    }
                    form = self.form_class(form_data, user=request.user)
                else:
                    form = self.form_class(user=request.user)

        # from CBV BaseListView
        self.object_list = self.get_queryset(
            business_slug=business_slug, offers_wants=offers_wants)
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            if (self.get_paginate_by(self.object_list) is not None and
                    hasattr(self.object_list, 'exists')):
                is_empty = not self.object_list.exists()
            else:
                is_empty = len(self.object_list) == 0
            if is_empty:
                raise Http404(_(
                    u"Empty list and '%(class_name)s.allow_empty' is False.")
                        % {'class_name': self.__class__.__name__})

        context = self.get_context_data(object_list=self.object_list)

        # inject validated form and filters
        context['search_term'] = self.search_term
        context['marketplace_form'] = form
        context['start_tab'] = start_tab

        # inject 'business tab here'
        if business_slug:
            try:
                context['business'] = CC3Profile.viewable.get(
                    slug=business_slug)
            except CC3Profile.DoesNotExist:
                raise Http404(_("Cannot find %s" % business_slug))
        context['offers_wants'] = offers_wants
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(MarketplaceView, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value

        return context


class MarketplaceSearchListView(ListView):
    """
    Marketplace search view. Renders the marketplace items returned after a
    search query by the user.

    Set up a form in the marketplace template, pointing to the URL of this view
    and having a single input text field with ``name="q"`` with the ``GET``
    method to have search features in the Marketplace if needed.

    PLEASE NOTE THIS is not very useful unless the marketplace doesnt' have
    any filtering (ie is simplistic, with no categories, communities,
    profile types, visibilty by community, pagination, ordering. Basically not
    to be used
    """
    model = Ad
    paginate_by = 12
    template_name = 'marketplace/ad_list.html'
    form_class = MarketplaceForm

    def get_queryset(self):
        query = self.request.GET.get('q', None)
        qset = (
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(created_by__first_name__icontains=query) |
            Q(created_by__last_name__icontains=query)
        )

        return Ad.objects.filter(status=AD_STATUS_ACTIVE).filter(qset)

    def get_context_data(self, **kwargs):
        context = super(MarketplaceSearchListView, self).get_context_data(
            **kwargs)

        context['marketplace_form'] = self.form_class(self.request.GET, user=self.request.user)

        return context


@login_required
@must_have_completed_profile
def pay(request, ad_id, template_name='marketplace/pay.html'):
    ad = get_object_or_404(Ad, pk=ad_id)
    ad_created_by = ad.created_by

    if ad_created_by.user == request.user:
        # can't buy own stuff
        return render_to_response(template_name, {
            'messages': [_(u'You cannot pay yourself')],
            'ad': ad
        }, context_instance=RequestContext(request))

    form_kwargs = {
        'description': ad.description,
        'contact_name': u"%s %s (%s)" % (ad_created_by.first_name,
                                         ad_created_by.last_name,
                                         ad_created_by.business_name),
        'amount': ad.price,
        'ad': ad.id
    }

    if request.method == "POST":
        form = MarketplacePayForm(form_kwargs, user=request.user)
        # if form validates - ie Company matches email, amount less than
        # available credit etc
        if form.is_valid():
            # make the payment
            sender = request.user
            business = None
            try:
                # brittle way of getting business name from bracketed string
                # could break if businesses have brackets in their name?
                contact_name = form.cleaned_data['contact_name']
                contact_name_business_name = contact_name[
                                             contact_name.index("(") +
                                             1:contact_name.rindex(")")]
                business = CC3Profile.viewable.get(
                    business_name__iexact=contact_name_business_name
                )
            except Exception: # CC3Profile.DoesNotExist:
                raise ValidationError(_('Please check the company name'))

            # messages.add_message(request, messages.WARNING,
            # _(u'Could not make payment at this time. (CC3Profile)'))

            receiver = business.user
            amount = form.cleaned_data['amount']
            description = ad.title
            try:
                if request.is_ajax():
                    # if we're dealing with ajax, wait for 2nd submit -
                    # where POST has 'confirmed key'
                    if not request.POST.has_key('confirmed'):
                        data = json.dumps({'success': True})
                        return HttpResponse(data, {
                            'content_type': 'application/json',
                        })

                transaction = backends.user_payment(
                    sender, receiver, amount, description)
                payment_log = AdPaymentTransaction.objects.create(
                    ad=ad,
                    title=ad.title,
                    amount=amount,
                    sender=sender,
                    receiver=receiver,
                    transfer_id=transaction.transfer_id
                )

                messages.add_message(
                    request, messages.INFO, _(u'Payment made successfully.'))
                return HttpResponseRedirect(
                    reverse('accounts_home'))
            except TransactionException, te:
                error_message = _('Could not make payment at this time.')

                if te.args[0].find('NOT_ENOUGH_CREDITS') != -1:
                    error_message = _('You do not have sufficient credit to '
                                      'complete the payment plus the '
                                      'transaction fee.')

                if request.is_ajax():
                    data = json.dumps({'errors': error_message})
                    return HttpResponse(data, {
                        'content_type': 'application/json',
                        'status': 400
                    })
                else:
                    messages.add_message(
                        request, messages.WARNING, error_message)
            except Exception, e:
                if request.is_ajax():
                    data = json.dumps(
                        {'errors': _(
                            u'Could not make payment at this time. '
                            u'(Backend unavailable)')})
                    return HttpResponse(data, {
                        'content_type': 'application/json',
                        'status': 400
                    })
                else:
                    messages.add_message(
                        request, messages.WARNING,
                        _(u'Could not make payment at this time. '
                          u'(Backend unavailable)'))
        else:
            if request.is_ajax():
                data = json.dumps(form.errors)
                response_kwargs = {
                    'status': 400,
                    'content_type': 'application/json'
                }
                return HttpResponse(data, **response_kwargs)
            else:

                messages.add_message(
                    request, messages.WARNING,
                    _(u'Could not make payment at this time.'))

    return render_to_response(template_name, {
        'form': MarketplacePayForm(form_kwargs, user=request.user),
        'ad': ad
    }, context_instance=RequestContext(request))


@login_required
@must_have_completed_profile
def want_contact_view(request, ad_id, form_class=WantContactForm,
                      template_name='marketplace/enquire.html',
                      success_url=None, extra_context=None,
                      fail_silently=False):
    """
    Taken from django contact form. not easily extendible as required here...

    Note: the email field is only shown and used for anonymous users.
    For authenticated users the emailaddress of the user is used.
    """

    ad = get_object_or_404(Ad, pk=ad_id)
    ad_created_by = ad.created_by

    # if user is not a consumer, show error message
    if not is_consumer_member(request.user):
        return render_to_response(template_name, {
            'messages': [_(u'Only consumers can enquire about adverts')]
        }, context_instance=RequestContext(request))

    if ad_created_by.user == request.user:
        # can't want own stuff
        return render_to_response(template_name, {
            'messages': [_(u'You cannot enquire about your own advert')]
        }, context_instance=RequestContext(request))

    is_authenticated = request.user.is_authenticated()

    if success_url is None:
        # Should no longer be required as we redirect back to the ad on success
        success_url = reverse('contact_form_sent')
    if request.method == 'POST':
        data = request.POST.copy()
        if is_authenticated:
            data["email"] = request.user.email
        form = form_class(data=data, files=request.FILES, request=request)
        if form.is_valid():
            form.save(fail_silently=fail_silently)
            messages.info(
                request, _(u"Thank you for your enquiry. "
                           u"An email has been sent to the advertiser"))
            return HttpResponseRedirect(ad.get_absolute_url())
        if is_authenticated:
            form.fields['email'] = u''
    else:
        form_data = {}
        if is_authenticated:
            # #3424 Display full name if advertiser is a consumer
            # Display business name otherwise
            if ad_created_by.user.get_profile().cyclos_group in settings.CYCLOS_CUSTOMER_MEMBER_GROUPS:
                name = ad_created_by.user.get_profile().full_name[:100]
            else:
                name = ad_created_by.user.get_profile().business_name[:100]
            form_data = {
                "name": name,
                "ad_id": ad.id

            }
        form = form_class(initial=form_data, request=request)
        if is_authenticated:
            form.fields['email'].required = False

    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(template_name,
                              {'form': form,
                               'ad': ad,
                               }, context_instance=context)


def business_profile(request, slug,
                     template_name='marketplace/business_profile.html'):

    business_cc3_profile = get_object_or_404(CC3Profile, slug=slug)
    business_ads = Ad.objects.filter(created_by__slug=slug)
    business_ads = business_ads.filter(status=AD_STATUS_ACTIVE)
    # todo: show inactive ads to business owner - is this done anywhere else?
    # if request.user != business_cc3_profile.user:
    # yes: inactive ads are shown to the business owner -
    # see the 'My Ads' link from the accounts sub menu
    latest_ads = business_ads.order_by(
        '-date_created')[:settings.PROFILE_MAX_NUMBER_OF_LATEST_ADS]

    offer_ads = business_ads.filter(adtype__code__iexact='O')
    wants_ads = business_ads.filter(adtype__code__iexact='W')
    form = CC3ProfileDisplayForm(instance=business_cc3_profile)

    # print type(business_cc3_profile.country)
    return render_to_response(template_name, {
        'business': business_cc3_profile,
        # 'business_country': business_cc3_profile.country,
        'latest_ads': latest_ads,
        'offer_ads_count': offer_ads.count(),
        'wants_ads_count': wants_ads.count(),
        'form': form
    }, context_instance=RequestContext(request))

#
# Campaigns
#


class CampaignView(CommunityNoFilterMixin, ListView):
    paginate_by = 12
    queryset = Campaign.objects.filter(status='V')
    extra_context = None
    template_name = 'marketplace/ad_list.html'
    form_class = CampaignFilterForm
    start_tab = u'campaigns'
    search_term = None

    ## Following functions are pulled out so that sites can
    ## override as needed
    def apply_categories_filter(self, campaigns, categories):
        children = []
        for category in categories:
            children += list(category.children.all())
        return campaigns.filter( Q(categories__in=categories) |
                                        Q(categories__in=children))

    def get_paginate_by(self, queryset):
        """
        Paginate by value saved to session, or use default class property value.
        """
        return self.request.session.get(
            'marketplace_paginate_by', self.paginate_by)

    def get_campaigns(self, categories, community, search_term):
        """
        Return a list of Campaigns, having appled the selected categories,
        from the marketplace-filter form, and sorted upcoming ones at the front,
        finished ones at the end
        """
        upcoming = []
        finished = []
        campaigns = Campaign.objects.exclude(status=CAMPAIGN_STATUS_HIDDEN)
        try:
            pass
            #community = self.request.user.get_profile().community
            #campaigns = campaigns.filter(communities=community)
        except (ObjectDoesNotExist, AttributeError):
            pass

        # filter
        if categories:
            campaigns = self.apply_categories_filter(campaigns, categories)

        if community:
            campaigns = campaigns.filter(communities__id__in=community)

        # search
        if search_term:
            campaigns = campaigns.filter(
                models.Q(title__icontains=search_term) |
                    models.Q(description__icontains=search_term) |
                    models.Q(contact_name__icontains=search_term) |
                    models.Q(contact_email__icontains=search_term)
            ).distinct()
            or_queries = []
            for bit in tokenize_regex.split(search_term.strip()):
                or_queries += [
                    models.Q(title__icontains=bit) |
                    models.Q(description__icontains=bit) |
                    models.Q(contact_name__icontains=bit) |
                    models.Q(contact_email__icontains=bit)
                ]
            campaigns = campaigns.filter(reduce(operator.or_, or_queries))

        # sort
        for item in campaigns.order_by('start_date', 'end_time').all():
            if item.has_finished:
                finished.append(item)
            else:
                upcoming.append(item)

        return upcoming + list(reversed(finished))

    def get(self, request, *args, **kwargs):
        search_form = MarketplaceSearchForm(request.GET)
        form_data = {}
        self.search_term = None
        if search_form.is_valid():
            self.search_term = search_form.cleaned_data['search']
            self.request.session['search_term'] = self.search_term
        elif 'search' in self.request.GET:
            self.search_term = None
            if 'search_term' in self.request.session:
                del request.session['search_term']
            request.session.modified = True
        elif 'search_term' in self.request.session:
            self.search_term = self.request.session['search_term']

        if request.method == 'GET':
            is_admin = False
            if self.request.user.is_authenticated():
                is_admin = (self.request.user.is_superuser or
                            self.request.user.is_community_admin())

            if request.user.is_authenticated() and \
                    request.GET.get('csrfmiddlewaretoken', None) is None and \
                    not is_admin:
                form_data = {
                    'community': [request.user.get_cc3_profile().community.id]
                }

            form_data.update(request.GET)

            form = self.form_class(form_data)

            # set some kwargs for the query set filtering
            if form.is_valid():
                if 'categories' in form.cleaned_data:
                    self.request.session['campaign_categories'] = \
                        form.cleaned_data['categories']

                if 'community' in form.cleaned_data:
                    self.request.session['campaign_community'] = \
                        form.cleaned_data['community']
            else:
                # If no paginate_by supplied, use the view default -- otherwise
                # switching between map and list view is problematic
                self.request.session['marketplace_paginate_by'] = \
                    self.paginate_by
                paginate_by = self.paginate_by

        '''
        if request.user.is_authenticated():
            form_data = {
                'community': [request.user.get_cc3_profile().community.id]
            }
        else:
            form_data = {}
        '''
        categories = self.request.session.get('campaign_categories', None)

        if categories:
            form_data['categories'] = categories
            form = self.form_class(form_data)
        else:
            form = self.form_class(form_data)

        community = self.request.session.get('campaign_community', None)

        self.object_list = self.get_campaigns(
            categories, community, self.search_term)
        context = self.get_context_data(object_list=self.object_list)

        # inject validated form and filters
        context['marketplace_form'] = form
        context['start_tab'] = self.start_tab
        context['search_term'] = self.search_term

        context['campaign_list'] = self.object_list
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CampaignView, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value
        return context


class MyCampaignsView(ListView):
    """Campaigns I am participating in"""
    model = Campaign
    extra_context = None
    paginate_by = 48   # will need to be cleverer wrt pagination/
                       # expired_campaigns if not all on one page
    template_name = 'accounts/my_campaigns.html'

    def dispatch(self, request, *args, **kwargs):
        # only for Individuals
        if user_can_join_campaigns(request.user):
            return super(MyCampaignsView, self).dispatch(
                request, *args, **kwargs)
        raise Http404

    def get_queryset(self):
        # all forthcoming campaigns I'm a participant of
        today = datetime.date.today()
        return Campaign.objects.filter(
                participants__profile=self.request.user.cc3_profile).exclude(
                start_date__lt=today).order_by('start_date', 'start_time')

    def get_context_data(self, **kwargs):
        context = super(MyCampaignsView, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value
        today = datetime.date.today()
        context['expired_campaigns'] = Campaign.objects.filter(
                participants__profile=self.request.user.cc3_profile).filter(
                start_date__lt=today).order_by('start_date', 'start_time')

        return context


class MyManagedCampaignsView(ListView):
    """Campaigns I created"""
    model = Campaign
    extra_context = None
    paginate_by = 24
    template_name = 'accounts/my_managed_campaigns.html'

    def dispatch(self, request, *args, **kwargs):
        """Check user is allowed to create Campaigns"""
        if user_can_own_campaigns(request.user):
            return super(MyManagedCampaignsView, self).dispatch(
                request, *args, **kwargs)
        raise Http404

    def get_queryset(self):
        # all campaigns created_by me
        return Campaign.objects.filter(
                created_by=self.request.user.cc3_profile).order_by(
                '-start_date', '-start_time')


class CampaignSubscribeView(UpdateView):
    model = Campaign
    form_class = CampaignSignupForm

    def dispatch(self, request, *args, **kwargs):
        campaign = self.get_object()
        if campaign.can_subscribe(request.user):
            return super(CampaignSubscribeView, self).dispatch(
                request, *args, **kwargs)
        else:
            raise PermissionDenied

    def form_valid(self, form):
        profile = self.request.user.cc3_profile
        campaign = form.instance
        if campaign.has_finished:
            messages.add_message(self.request, messages.ERROR, _(
                u'This activity has finished -- you cannot sign up'))
        elif campaign.has_participant(profile):
            messages.add_message(self.request, messages.INFO, _(
                u'You are already signed up'))
        elif campaign.num_participants_required <= 0:
            messages.add_message(self.request, messages.ERROR, _(
                u'This activity is full -- you cannot sign up'))
        else:
            campaign.add_participant(profile)
            messages.add_message(self.request, messages.INFO, _(
                    u'Thank you for signing up. The contact has received an '
                    u'email with your name and email address and can contact '
                    u'you.'))

        campaign.send_signup_notifications(profile=profile)

        return HttpResponseRedirect(self.get_success_url())


class CampaignUnsubscribeView(UpdateView):
    model = Campaign
    form_class = CampaignSignupForm

    def form_valid(self, form):
        profile = self.request.user.cc3_profile
        campaign = form.instance
        if campaign.has_finished:
            messages.add_message(self.request, messages.ERROR, _(
                u'This activity has finished -- you cannot unsubscribe'))
        elif not campaign.has_participant(profile):
            messages.add_message(self.request, messages.INFO, _(
                u'You are not currently signed up'))
        else:
            campaign.remove_participant(profile)
            messages.add_message(self.request, messages.INFO, _(
                    u'Unsubscribing you'))
        return HttpResponseRedirect(self.get_success_url())


class CampaignDetail(DetailView):
    model = Campaign
    template_name = 'marketplace/campaign_detail.html'

    def dispatch(self, request, *args, **kwargs):
        campaign = self.get_object()
        if campaign.can_see(request.user):
            return super(CampaignDetail, self).dispatch(
                request, *args, **kwargs)
        else:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super(CampaignDetail, self).get_context_data(**kwargs)

        if self.request.user.is_authenticated():
            if hasattr(self.request.user, 'cc3_profile') and \
                    context['object'].has_participant(
                        self.request.user.cc3_profile):
                context['already_subscribed'] = True
            context['is_consumer_member'] = is_consumer_member(
                self.request.user)
            context['is_same_community'] = context['object'].is_same_community(
                self.request.user)
            context['logged_in'] = True
        return context


class CampaignManageParticipantsView(CampaignDetail):
    template_name = 'marketplace/campaign_manage_participants.html'

    def dispatch(self, request, *args, **kwargs):
        campaign = self.get_object()
        if campaign.can_edit(request.user):
            return super(CampaignManageParticipantsView, self).dispatch(
                request, *args, **kwargs)
        else:
            raise PermissionDenied


def _get_rewards_from_formset(formset):
    total = Decimal(0)
    reward_amounts = {}
    for form in formset:
        dummy_p = form.save(commit=False)
        reward = dummy_p.get_reward_due()
        reward_amounts[dummy_p.pk] = reward
        total += reward
    return total, reward_amounts


def campaign_manage_rewards(request, pk):

    campaign = get_object_or_404(Campaign, pk=pk)
    if not campaign.can_edit(request.user):
        raise PermissionDenied

    context = {
        "object": campaign,
        "default_start_time": campaign.start_time,
        "default_end_time": campaign.end_time,
        "default_payment": "{0}".format(campaign.reward_per_participant),
        "default_seconds": "{0}".format(int(campaign.get_default_seconds())),
    }

    ParticipantInlineFormSet = inlineformset_factory(
        Campaign, CampaignParticipant,
        form=RewardCampaignParticipantForm, can_delete=False, extra=0)

    # exclude any that have already been paid
    queryset=CampaignParticipant.objects.filter(campaign=campaign,
                                                date_rewarded__isnull=True)
    context['paid_participants'] = CampaignParticipant.objects.filter(
        campaign=campaign, date_rewarded__isnull=False)

    populate_fields = 'false'   # for js

    if request.method == "POST":

        if "payment_cancelled" in request.POST:
            messages.warning(
                request, _(u"Reward payments cancelled"))
            return HttpResponseRedirect(
                reverse('accounts-manage-campaign-rewards',
                        kwargs={'pk': campaign.pk}))

        formset = ParticipantInlineFormSet(
            request.POST, instance=campaign, prefix="sub",
            queryset=queryset,
            )
        if formset.is_valid():
            if "payment_confirmed" in request.POST:
                # save all (changed) start and end times
                # (others will remain as null)
                formset.save()
                # make the reward payments
                total_payments = campaign.make_reward_payments()
                messages.success(
                    request,
                    _(u"Made reward payments of {0} {1}".format(
                        total_payments,
                        getattr(settings, 'CURRENCY_NAME', 'punten')))
                    )
                return HttpResponseRedirect(
                    reverse('accounts-manage-campaign-rewards',
                            kwargs={'pk': campaign.pk}))
            else:
                context['confirmation_required'] = True
                total_amount, reward_amounts = _get_rewards_from_formset(
                    formset)
                context['total_amount'] = total_amount
                context['reward_amounts'] = reward_amounts
    else:
        populate_fields = 'true'
        formset = ParticipantInlineFormSet(
            instance=campaign, prefix="sub", queryset=queryset)

    if getattr(settings, 'CC3_CURRENCY_INTEGER_ONLY', False):
        context['decimal_places'] = 0
    else:
        context['decimal_places'] = 2
    context['formset'] = formset
    context['populate_fields'] = populate_fields
    return render(request, "marketplace/campaign_manage_rewards.html", context)


class CampaignCreateView(MarketplaceAdCreateView):
    form_class = CampaignForm
    model = Campaign
    template_name = 'marketplace/campaign_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Check user is allowed to create Campaigns
        """
        if user_can_own_campaigns(request.user):
            return super(CampaignCreateView, self).dispatch(
                request, *args, **kwargs)
        raise Http404

    def get_initial(self):
        initial = super(CampaignCreateView, self).get_initial()
        profile = self.request.user.get_profile()
        initial['contact_name'] = profile.name
        initial['country'] = profile.country
        initial['city'] = profile.city
        initial['address'] = profile.address
        initial['postal_code'] = profile.postal_code
        return initial

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.created_by = request.user.get_profile()
            if 'save_hidden' in request.POST:
                self.object.status = CAMPAIGN_STATUS_HIDDEN
            elif 'save_published' in request.POST:
                self.object.status = CAMPAIGN_STATUS_VISIBLE
            self.object.save()
            form.save_m2m()  # communities, categories
            num_sent = self.object.send_creation_notifications()
            if num_sent:
                LOG.info(
                    "Sent {0} email notifications of new campaign".format(
                    num_sent))
            return self.form_valid(form)

        return self.form_invalid(form)

    def get_success_url(self):
        return reverse('accounts_my_managed_campaigns')

    def get_context_data(self, **kwargs):
        """add flag to control display of Save buttons"""
        context = super(CampaignCreateView, self).get_context_data(
            **kwargs)
        context['is_published'] = False
        return context


class CampaignUpdateView(UpdateView):
    form_class = CampaignForm
    model = Campaign
    template_name = 'marketplace/campaign_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Check user is allowed to edit this Campaign
        """
        campaign = self.get_object()
        if campaign.can_edit(self.request.user):
            return super(CampaignUpdateView, self).dispatch(
                request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_success_url(self):
        return reverse('accounts_my_managed_campaigns')

    def form_valid(self, form):
        retval = super(CampaignUpdateView, self).form_valid(form)
        if 'save_hidden' in self.request.POST:
            self.object.status = CAMPAIGN_STATUS_HIDDEN
            self.object.save()
        elif 'save_published' in self.request.POST:
            self.object.status = CAMPAIGN_STATUS_VISIBLE
            self.object.save()
        # send email to participants
        self.object.notify_participants_of_update()
        return retval

    def get_context_data(self, **kwargs):
        """add flag to control display of Save buttons"""
        context = super(CampaignUpdateView, self).get_context_data(
            **kwargs)
        context['is_published'] = self.object.is_visible
        return context

    #def render_to_json_response(self, context, formset=None, **response_kwargs):
    #    # TODO: To be reviewed... and probably moved. Deprecated formset stuff.
    #    if formset:
    #        data = u"%s%s%s" % (
    #            '{"captions": ["',
    #            _("Please make sure you have added captions for all your images."),
    #            '"]}')
    #    else:
    #        data = json.dumps(context)
    #
    #    response_kwargs['content_type'] = 'application/json'
    #    return HttpResponse(data, **response_kwargs)


class CancelCampaignView(UpdateView):
    # TODO: check it's in the future
    model = Campaign
    form_class = CancelCampaignForm
    extra_context = None
    template_name = 'marketplace/cancel_campaign.html'

    def dispatch(self, request, *args, **kwargs):
        # campaign must not be finished/cancelled, and user
        # must have edit rights
        campaign = self.get_object()
        if campaign.is_live and campaign.can_edit(self.request.user):
            return super(CancelCampaignView, self).dispatch(
                request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_success_url(self):
        return reverse('accounts_my_managed_campaigns')

    def form_valid(self, form):
        self.object.status = CAMPAIGN_STATUS_CANCELLED
        # send email to participants
        self.object.notify_participants_of_cancellation()
        return super(CancelCampaignView, self).form_valid(form)


class RemoveCampaignParticipantView(UpdateView):
    model = CampaignParticipant
    form_class = RemoveCampaignParticipantForm
    template_name = 'marketplace/campaignparticipant_confirm_delete.html'

    def dispatch(self, request, *args, **kwargs):
        # campaign must not be finished/cancelled, and user
        # must have edit rights
        campaign = self.get_object().campaign
        if campaign.is_live and campaign.can_edit(self.request.user):
            return super(RemoveCampaignParticipantView, self).dispatch(
                request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_success_url(self):
        return reverse('accounts-manage-campaign-participants',
                       kwargs={'pk': self.campaign_pk})

    def form_valid(self, form):
        reason = form.cleaned_data.get('why_removed', '')
        LOG.debug("Reason for removing participant: {0}".format(reason))
        # send email to participant
        self.object.notify_participant_of_removal(reason=reason)
        # build message
        msg = _(u"Participant {0} has been removed and notified".format(
            self.object.profile.full_name))
        self.campaign_pk = self.object.campaign.pk
        # finally, delete the CampaignParticipant
        LOG.debug("About to delete {0}".format(self.object))
        self.object.delete()
        #self.object.campaign.remove_participant(self.object.profile)
        messages.success(self.request, msg)
        return HttpResponseRedirect(self.get_success_url())
