from django.conf.urls import patterns, url, include

from rest_framework import routers

from cc3.invoices.views_api import CurrenciesAPIViewSet

from .views_api import CategoriesListAPIView


router = routers.DefaultRouter()
router.register(r'currencies', CurrenciesAPIViewSet, base_name="currencies")


urlpatterns = patterns('',
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    url(r'^api/categories/$', CategoriesListAPIView.as_view(),
        name='api_categories'),
    url(r'^api/', include('cc3.accounts.urls_api')),
    url(r'^api/', include('cc3.marketplace.urls_api')),
    url(r'^api/', include(router.urls)),
)
