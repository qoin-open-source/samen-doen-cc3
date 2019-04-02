from django.conf.urls import patterns, url

from .views_api import CommunityAdImageListView, CommunityAdImagesView


urlpatterns = patterns(
    '',
    url(r'^ad_images/$', CommunityAdImageListView.as_view(),
        name='api_comm_adimage_list'),
    url(r'^ad_images/(?P<ad>\d+)/$', CommunityAdImagesView.as_view(),
        name='api_comm_ad_images'),
)
