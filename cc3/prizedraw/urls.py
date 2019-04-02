from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .views import (
    PrizeDrawHomeView, BuyTicketsFormView, MyPastResultsView,
    MyRepeatPurchasesView, CancelRepeatPurchaseView, current_draw_info)

urlpatterns = patterns(
    '',
    url(r'^$', login_required(PrizeDrawHomeView.as_view()),
        name='prizedraw_home'),
    url(r'^buy-tickets/$', login_required(BuyTicketsFormView.as_view()),
        name='prizedraw_buy_tickets'),
    url(r'^my-results/$', login_required(MyPastResultsView.as_view()),
        name='prizedraw_my_results'),
    url(r'^my-repeat-purchases/$', login_required(
        MyRepeatPurchasesView.as_view()), name="prizedraw_my_repeat_purchases"),
    url(r'^cancel-repeat-purchase/$', login_required(
        CancelRepeatPurchaseView.as_view()),
        name="prizedraw_cancel_repeat_purchase"),
    url(r'^cancel-repeat-purchase/(?P<pk>\d+)/$', login_required(
        CancelRepeatPurchaseView.as_view()),
        name="prizedraw_cancel_repeat_purchase_direct"),
    url(r'^current_draw_info', current_draw_info,
        name="prizedraw_current_draw_info"),
)
