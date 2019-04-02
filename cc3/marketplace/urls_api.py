from django.conf.urls import include, patterns, url

from rest_framework import routers

from .views_api import (
    AdAPIViewSet, AdTypeListAPIView, AdListAPIView, MarketplaceAdImageListView,
    MarketplaceAdImagesView)


router = routers.DefaultRouter()
router.register(r'ads', AdAPIViewSet, base_name='ads')


urlpatterns = patterns(
    '',
    url(r'^mktad_images/$', MarketplaceAdImageListView.as_view(),
        name='api_marketplace_adimage_list'),
    url(r'^mktad_images/(?P<ad>\d+)/$', MarketplaceAdImagesView.as_view(),
        name='api_marketplace_ad_images'),
    url(r'^mktad_images/new/$', MarketplaceAdImagesView.as_view(),
        name='api_marketplace_new_ad_images'),
    url(r"mktad_types/$", AdTypeListAPIView.as_view(),
        name="ads_types"),
    url(r"mktads/list/$", AdListAPIView.as_view(),
        name="api_ads"),
    url(r"mktads/list/account/(?P<pk>\d+)/$", AdListAPIView.as_view(),
        name="api_ads_account"),
    url(r'^', include(router.urls)),
)
