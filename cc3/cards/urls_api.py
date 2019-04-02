from django.conf.urls import patterns, url

from .views_api import (
    TerminalLoginView, OperatorLoginView, UserLoginView, NewAccountView)
from .views_api import (
    CardRegisterView, CardDetailView, CardPaymentView, CardPermittedDetailView,
    CardRewardView, )


urlpatterns = patterns(
    '',
    url(r'^terminal/login/$', TerminalLoginView.as_view(),
        name='api_cards_terminal_login'),
    url(r'^operator/login/$', OperatorLoginView.as_view(),
        name='api_cards_operator_login'),
    url(r'^user/login/$', UserLoginView.as_view(),
        name='api_cards_user_login'),
    url(r'^card/$', CardRegisterView.as_view(),
        name='api_cards_card_register'),
    url(r'^card/(?P<card_number>\w+)/$', CardDetailView.as_view(),
        name='api_cards_card_detail'),
    url(r'^card/(?P<card_number>\w+)/permitted/$',
        CardPermittedDetailView.as_view(),
        name='api_cards_card_permitted_detail'),
    url(r'^card/(?P<card_number>\w+)/new_account/$', NewAccountView.as_view(),
        name='api_cards_card_new_account_detail'),
    url(r'^card/(?P<card_number>\w+)/payment/$', CardPaymentView.as_view(),
        name='api_cards_card_payment'),
    url(r'^card/(?P<card_number>\w+)/reward/$', CardRewardView.as_view(),
        name='api_cards_card_reward'),
)
