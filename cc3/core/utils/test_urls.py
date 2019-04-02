from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

admin.autodiscover()


urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^/', RedirectView.as_view(url='/marketplace/'), name='pages-root'),
    # url(r'^register/', include('cc3.registration.backends.qoinware.urls')),
    # url(r'^marketplace/', include('cc3.marketplace.urls')),
    # url(r'^accounts/', include('cc3.accounts.urls')),
    url(r'^comm/', include('cc3.communityadmin.urls',
                           namespace='communityadmin_ns')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog',
        {'packages': ('cc3.marketplace',)}),

    # API endpoints.
    url(r'^api/comm/', include('cc3.communityadmin.urls_api')),
    url(r'^api/marketplace/', include('cc3.marketplace.urls_api')),
    url(r'^api/v1/cards/', include('cc3.cards.urls_api')),
    url(r'^api/v1/rewards/', include('cc3.rewards.urls_api')),
    url(r'^api/v1/files/', include('cc3.files.urls_api')),
)

urlpatterns += patterns(
    '',
    url(r'^', include('django.contrib.auth.urls')),
    url(r'^password_reset/$', auth_views.password_reset,
        name="auth_password_reset"),
    url(r'^login/$', auth_views.login, {
        'template_name': 'registration/login.html',
    }, name='auth_login'),
    url(r'^password_reset/$', auth_views.password_reset,
        name="auth_password_reset"),
    url(r'^password_change/$', auth_views.password_change,
        name="auth_password_change"),
    url(r'^', include('cc3.registration.backends.qoinware.urls')),

    url(r'^cards/', include('cc3.cards.urls')),
    url(r'^rewards/', include('cc3.rewards.urls')),
    url(r'^marketplace/', include('cc3.marketplace.urls')),
    url(r'^accounts/', include('cc3.accounts.urls')),
    url(r'^content/', include('cc3.cmscontent.urls')),
    url(r'^invoices/', include('cc3.invoices.urls'))
)
