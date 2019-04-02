from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from .decorators import must_have_completed_profile

from cc3.core.views import DirectTemplateView
from cc3.marketplace.views import (
    MarketplaceAdCreateView, AdListView, MarketplaceAdDisableView,
    MarketplaceAdToggleStatusView, MarketplaceAdUpdateView,
    MyCampaignsView, MyManagedCampaignsView,
    CampaignCreateView, CampaignUpdateView, CancelCampaignView,
    CampaignManageParticipantsView, RemoveCampaignParticipantView,
    campaign_manage_rewards,
)
from cc3.billing.views import (
    MyProductsListView, MyProductsInvoiceView
)
from .views import (
    update_my_profile, TransactionsListView, AddFunds, contact_name_auto,
    want_credit_view, CloseAccountView, AccountSecurityView, PayDirectFormView,
    TransactionsSearchListView, ExchangeToMoneyView, TimeoutView,
    TransactionsMonthlyPDFView, TransactionsLast10PDFView,
    TransactionsExportView, ReallyCloseAccountView,
    AccountStatsView,
)


urlpatterns = patterns(
    '',
    url(r'^profile/', update_my_profile, name='accounts-update-profile'),

    url(r'^credit/$', want_credit_view,  # login_required(want_credit_view),
        # NB want_credit_view has login_required decorator
        name='accounts-credit'),
    url(r'^credit/sent/$',
        login_required(DirectTemplateView.as_view(
            template_name='accounts/credit_sent.html')),
        name='accounts-credit-sent'),

    url(r'^credit/applied/$',
        login_required(DirectTemplateView.as_view(
            template_name='accounts/apply_sent.html')),
        name='accounts-apply-sent'),

    url(r'^add-funds/$',
        login_required(AddFunds.as_view()),
        name='add-funds'),

    url(r'^my-ads/$',
        login_required(must_have_completed_profile(AdListView.as_view())),
        name='accounts_my_ads'),

    # Catch the my-ads sorting view,
    url(r'^my-ads/([\w-]+)/([\w-]+)/$',
        login_required(must_have_completed_profile(AdListView.as_view())),
        name="accounts_my_ads_sorted"),

    url(r'^place-ad/$',
        login_required(must_have_completed_profile(
            MarketplaceAdCreateView.as_view())),
        name='accounts_place_ad'),

    url(r'^edit-ad/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            MarketplaceAdUpdateView.as_view())),
        name='accounts_edit_ad'),

    url(r'^toggle-ad/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            MarketplaceAdToggleStatusView.as_view())),
        name='accounts_toggle_ad'),

    # Do not allow users to delete ads, only disable them.
    url(r'^disable-ad/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            MarketplaceAdDisableView.as_view())),
        name='accounts-disable-ad'),

    url(r'^activities/$',
        login_required(must_have_completed_profile(
            MyManagedCampaignsView.as_view())),
        name='accounts_my_managed_campaigns'),

    url(r'^my-activities/$',
        login_required(must_have_completed_profile(
            MyCampaignsView.as_view())),
        name='accounts_my_campaigns'),

    url(r'^new-activity/$',
        login_required(must_have_completed_profile(
            CampaignCreateView.as_view())),
        name='accounts-new-campaign'),

    url(r'^edit-activity/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            CampaignUpdateView.as_view())),
        name='accounts-edit-campaign'),

    url(r'^activities/manage-participants/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            CampaignManageParticipantsView.as_view())),
        name='accounts-manage-campaign-participants'),

    url(r'^activities/manage-rewards/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            campaign_manage_rewards)),
        name='accounts-manage-campaign-rewards'),

    url(r'^activities/remove-participant/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            RemoveCampaignParticipantView.as_view())),
        name='accounts-remove-campaign-participant'),

    url(r'^cancel-activity/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            CancelCampaignView.as_view())),
        name='accounts-cancel-campaign'),

    url(r'^pay-direct/$',
        login_required(must_have_completed_profile(
            PayDirectFormView.as_view())),
        name='accounts_pay_direct'),

    # Accounts home - Transactions view.
    url(r'^$',
        login_required(must_have_completed_profile(
            TransactionsListView.as_view())
        ),
        name='accounts_home'),

    url(r'^transactions/$',
        login_required(must_have_completed_profile(
            TransactionsSearchListView.as_view())
        ),
        name='accounts_transactions_search'),

    url(r'^transactions/monthly/$',
        login_required(must_have_completed_profile(
            TransactionsMonthlyPDFView.as_view())
        ),
        name='accounts_transactions_monthly_pdf'),

    url(r'^transactions/last10/$',
        login_required(must_have_completed_profile(
            TransactionsLast10PDFView.as_view())
        ),
        name='accounts_transactions_last_10_pdf'),

    url(r'^transactions/export/$',
        login_required(must_have_completed_profile(
            TransactionsExportView.as_view())
        ),
        name='accounts_transactions_export'),

    url(r'^statistics/$',
        login_required(must_have_completed_profile(
            AccountStatsView.as_view())
        ),
        name='accounts_stats_summary'),

    # Products views

    url(r'^products/$',
        login_required(must_have_completed_profile(
            MyProductsListView.as_view())
        ),
        name='accounts_products'),
    url(r'^products/invoice/(?P<pk>\d+)/$',
        login_required(must_have_completed_profile(
            MyProductsInvoiceView.as_view())
        ),
        name='accounts_products_invoice'
    ),
    # AJAX info.
    url(r'^contact_name_auto/(?P<community>\d+)/$',
        login_required(must_have_completed_profile(contact_name_auto)),
        name='contact_name_auto'),

    url(r'^contact_name_auto/',
        login_required(must_have_completed_profile(contact_name_auto)),
        name='contact_name_auto'),

    # Catch the sorting view, placed last to avoid upsetting other possible
    # URLs.
    url(r'^([\w-]+)/([\w-]+)/$',
        login_required(must_have_completed_profile(
            TransactionsListView.as_view())
        ),
        name="accounts_home_sorted"),

    url(r'^close-account/$',
        login_required(must_have_completed_profile(
            CloseAccountView.as_view())), name='accounts_close'),

    url(r'^close-my-account/$',
        login_required(must_have_completed_profile(
            ReallyCloseAccountView.as_view())), name='accounts_really_close'),

    url(r'^account-closed/$',
        DirectTemplateView.as_view(
            template_name='accounts/really_close_account_done.html'),
        name='accounts_really_close_done'),

    url(r'^security/$',
        login_required(must_have_completed_profile(
            AccountSecurityView.as_view(),
            # template_name='accounts/accounts_security.html'),
        )), name='accounts_security'),

    url(r'^exchange-to-money/$',
        login_required(
            ExchangeToMoneyView.as_view()
        ), name='exchange-to-money'),

    url(r'^timeout/$',
        TimeoutView.as_view(), name="accounts_timeout"
    )
)
