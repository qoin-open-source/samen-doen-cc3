from django.conf.urls import include, patterns, url

from rest_framework import routers

from .views_api import (
    AccountsAPIViewSet, AccountAPIView, TransactionsListAPIView,
    PayDirectAPIView)


router = routers.DefaultRouter()
router.register(r'accounts', AccountsAPIViewSet, base_name="account")


urlpatterns = patterns(
    '',
    url(r"account/$", AccountAPIView.as_view(),
        name="api_account"),
    url(r"transactions/$", TransactionsListAPIView.as_view(),
        name="api_transactions"),
    url(r"pay_direct/$", PayDirectAPIView.as_view(),
        name="api_pay_direct"),
    url(r'^', include(router.urls)),
)
