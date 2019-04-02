from django.conf.urls import patterns, url

from .views_api import JoinCauseAPIView


urlpatterns = patterns(
    '',
    url(r'causes/join/(?P<cause_pk>\d+)/$', JoinCauseAPIView.as_view(),
        name='api_rewards_causes_join'),
)
