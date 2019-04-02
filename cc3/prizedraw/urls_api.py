# encoding: utf-8
from django.conf.urls import patterns, url

from .views_api import (
    CardPrizeDrawPaymentView, PrizeDrawLoginView, ValidateUserCanBuyView,
    RegisterNewUserView, CreditUserView, PurchaseTicketsView,
    CardPrizeDrawCreditUserView
)


urlpatterns = patterns(
    '',
    url(r'^card/(?P<card_number>\w+)/payment/$',
        CardPrizeDrawPaymentView.as_view(),
        name='api_prizedraw_card_payment'),

    url(r'^card/(?P<card_number>\w+)/credit/$',
        CardPrizeDrawCreditUserView.as_view(),
        name='api_prizedraw_card_credit_user'),

    url(r'^login/$',
        PrizeDrawLoginView.as_view(),
        name='api_prizedraw_login'),

    url(r'^validate_user_can_buy/$',
        ValidateUserCanBuyView.as_view(),
        name='api_prizedraw_validate_user_can_buy'),

    url(r'^register_new_user/$',
        RegisterNewUserView.as_view(),
        name='api_prizedraw_register_new_user'),

    url(r'^credit_user/$',
        CreditUserView.as_view(),
        name='api_prizedraw_credit_user'),

    url(r'^purchase_tickets/$',
        PurchaseTicketsView.as_view(),
        name='api_prizedraw_purchase_tickets'),

)
