from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from .views import (bulk_reward_upload_wizard, UpdateDonationPercentageView,
    JoinCauseView, SearchCauseListView, SelectCauseListView, admin_causes_list)


urlpatterns = patterns(
    '',
    url(r'^causes/$', login_required(SelectCauseListView.as_view()),
        name='causes_list'),
    url(r'^causes/join/(?P<cause_pk>\d+)/$',
        login_required(JoinCauseView.as_view()),
        name='join_cause'),
    url(r'^causes/percentage/$',
        login_required(UpdateDonationPercentageView.as_view()),
        name='update_donation_percentage'),
    url(r'^causes/search/$', login_required(SearchCauseListView.as_view()),
        name='search_cause'),
    url(r'^rewards/bulk_upload/$', login_required(bulk_reward_upload_wizard),
        name='rewards_bulk_upload'),
    url(r'^admin/causes_list/$', admin_causes_list, name='admin_causes_list'),
)
