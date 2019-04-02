from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from cc3.accounts.decorators import must_have_completed_profile

from .views import (
    AdDetail, BusinessView, MarketplaceView, pay, want_contact_view,
    business_profile, BusinessMapView, MarketplaceSearchListView,
    CampaignView, CampaignDetail,
    CampaignSubscribeView, CampaignUnsubscribeView)


urlpatterns = patterns(
    '',
    # list view
    url(r'^$',
        MarketplaceView.as_view(),
        name='marketplace'),

    url(r'^ads/$',
        MarketplaceView.as_view(),
        name='marketplace-ads'),

    url(r'^businesses/map/$',
        BusinessMapView.as_view(),
        name='businesses-map'),

    # detail view
    url(r'^detail/(?P<pk>\d+)/$',
        AdDetail.as_view(template_name='marketplace/detail.html'),
        name='marketplace-detail'),

    url(r'^pay/(?P<ad_id>\d+)/$',
        pay,  # NB 'pay' view has login_required decorator, so unnecessary here
        #login_required(pay),
        name='marketplace-pay'),

    url(r'^enquire/(?P<ad_id>\d+)/$',
        want_contact_view,  # NB 'want_contact_view' view has login_required
        # decorator, so unnecessary here
        #login_required(want_contact_view),
        name='marketplace-enquire'),
    url(r'^enquire/sent/$',
        login_required(
            TemplateView.as_view(template_name='marketplace/enquire_sent.html')
        ),
        name='contact_form_sent'),

    url(r'^businesses/$',
        BusinessView.as_view(),
        name='business-targetted'),

    # alternative url for view of 'profiles' rather than ads (businesses a
    # more specific form or profile - incidentally only type of profile in
    # first system developed
    # included here as profielen - as Dutch only language project using this,
    # and attempt at using ugettext_lazy to translate URL failed.
    url(r'^profielen/$',
        BusinessView.as_view(),
        name='profielen-targetted'),

    url(r'^profielen/map/$',
        BusinessMapView.as_view(),
        name='profielen-map'),

    url(r'^activities/$',
        CampaignView.as_view(),
        name='campaign-list'),

    url(r'^activities/detail/(?P<pk>\d+)/$',
        CampaignDetail.as_view(),
        name='campaign-detail'),

    url(r'^activities/signup/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            CampaignSubscribeView.as_view())),
        name='campaign-subscribe'),

    url(r'^activities/unsubcribe/(?P<pk>\d+)/$',
        login_required(CampaignUnsubscribeView.as_view()),
        name='campaign-unsubscribe'),

    # Search form action.
    url(r'^search/$', MarketplaceSearchListView.as_view(),
        name='marketplace-search'),

    # list view - catch with businesses or products-and-services
    url(r'^([\w-]+)/$',  # TODO: this regex should have a prefix of some sort for safety
        MarketplaceView.as_view(),
        name='marketplace-targetted'),

    url(r'^profile/(?P<slug>[-\w]+)/$', business_profile,
        name='marketplace-business-profile'),

    # list view - catch with businesses or products-and-services
    url(r'^([\w-]+)/([\w-]+)/$',  # TODO: this regex should have a prefix of some sort for safety
        MarketplaceView.as_view(),
        name='marketplace-targetted-business'),
)
