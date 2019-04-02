from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from .views import (
    NFCTerminalsListView, OperatorCreateView, OperatorDeleteView,
    OperatorUpdateView, CardFulfillmentListView, OwnerManageCardView,
    owner_register_card, OwnerManageAndRegisterCardsView,
    TransactionsXReport, TransactionsZReport, OwnerBlockUnblockCardView)


urlpatterns = patterns(
    '',
    url(r'^terminals/$', login_required(NFCTerminalsListView.as_view()),
        name='terminals_list'),
    url(r'^operators/add/$', login_required(OperatorCreateView.as_view()),
        name='operator_create'),
    url(r'^operators/(?P<pk>\d+)/$',
        login_required(OperatorUpdateView.as_view()),
        name='operator_update'),
    url(r'^operators/(?P<pk>\d+)/delete/$',
        login_required(OperatorDeleteView.as_view()),
        name='operator_delete'),
    url(r'^manage/$', login_required(OwnerManageAndRegisterCardsView.as_view()),
        name='owner_manage_and_register_cards'),
    url(r'^manage_card/$', login_required(OwnerManageCardView.as_view()),
        name='owner_manage_card'),
    url(r'^block/(?P<pk>\d+)/$',
        login_required(OwnerBlockUnblockCardView.as_view(action='block')),
        name='owner_block_card'),
    url(r'^unblock/(?P<pk>\d+)/$',
        login_required(OwnerBlockUnblockCardView.as_view(action='unblock')),
        name='owner_unblock_card'),
    url(r'^register_card/$', login_required(owner_register_card),
        name='owner_register_card'),
    url(r'^register_card/success/$', login_required(TemplateView.as_view(
        template_name="cards/owner_register_card_success.html")
    ), name='owner_register_card_success'),
    url(r'^fulfillment/$', login_required(CardFulfillmentListView.as_view()),
        name='cardfulfillment'),
    url(r'^x_report/$', login_required(TransactionsXReport.as_view()),
        name='cards_x_report'),
    url(r'^z_report/$', login_required(TransactionsZReport.as_view()),
        name='cards_z_report'),
)
