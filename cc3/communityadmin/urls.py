from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from .views import (
    MemberListView, TransactionListView, WantsOffersListView,
    ChangePasswordView, update_profile, MemberTransactionsView, EditContent,
    MemberWantsOffersView, created_by_auto, CommunityAdUpdateView, AdCreate,
    CommunityAdminAdDisableView, AdHold, ContentListView, ChangeGroupView,
    create_member_wizard, categories_auto,
    CategoriesReportView, WantCategoriesReportView, OfferCategoriesReportView)


urlpatterns = patterns(
    '',
    url(r'^members/$', MemberListView.as_view(), name='memberlist'),
    url(r'^members/([\w-]+)/([\w-]+)/$', MemberListView.as_view(),
        name="memberlist_sorted"),
    url(r'^transactions/$', TransactionListView.as_view(),
        name='transactions'),
    url(r'^wantsoffers/$', WantsOffersListView.as_view(),
        name='wantsoffers'),
    url(r'^content/$', ContentListView.as_view(),
        name='contentlist'),
    url(r'^categories/$', CategoriesReportView.as_view(),
        name='categoriesreport'),
    url(r'^wantcategories/$', WantCategoriesReportView.as_view(),
        name='wantcategoriesreport'),
    url(r'^offercategories/$', OfferCategoriesReportView.as_view(),
        name='offercategoriesreport'),

    url(r'^addmember/$', create_member_wizard, name='addmember'),
    url(r'^editmember/(?P<username>[_@\+\.\-\w]+)/$', update_profile,
        name='editmember'),
    url(r'^changepassword/(?P<username>[_@\+\.\-\w]+)/$',
        ChangePasswordView.as_view(),
        name='changepassword'),
    url(r'^transactions/(?P<username>[_@\+\.\-\w]+)/$',
        MemberTransactionsView.as_view(),
        name='membertransactions'),
    url(r'^wantsoffers/(?P<username>[_@\+\.\-\w]+)/$',
        MemberWantsOffersView.as_view(),
        name='memberwantsoffers'),
    url(r'^changegroup/(?P<username>[_@\+\.\-\w]+)/$',
        ChangeGroupView.as_view(),
        name='changegroup'),

    url(r'^edit-ad/(?P<pk>\d+)/$', CommunityAdUpdateView.as_view(),
        name='edit_ad'),
    url(r'^place-ad/$', AdCreate.as_view(), name='place-ad'),

    url(r'^disable-ad/(?P<pk>\d+)/$', CommunityAdminAdDisableView.as_view(),
        name='disable-ad'),
    url(r'^hold-ad/(?P<pk>\d+)/$', AdHold.as_view(), name='hold-ad'),

    url(r'^edit-content/(?P<pk>\d+)/$', EditContent.as_view(),
        name='edit-content'),

    url(r'^created_by_auto/$', login_required(created_by_auto),
        name='created_by_auto'),
    url(r'^categories_auto/$', login_required(categories_auto),
        name='categories_auto'),
)
