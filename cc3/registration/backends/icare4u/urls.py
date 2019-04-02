"""
URLconf for registration and activation, using django-registration's
default backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^accounts/', include('registration.backends.default.urls')),

This will also automatically set up the views in
``django.contrib.auth`` at sensible default locations.

If you'd like to customize registration behavior, feel free to set up
your own URL patterns for these views instead.

"""


from django.conf.urls import patterns
from django.conf.urls import include
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView

from registration.backends.default.views import ActivationView
from cc3.accounts.forms import CC3SetPasswordForm, CC3PasswordChangeForm


urlpatterns = patterns(
    '',
    url(r'^activate/complete/$',
        TemplateView.as_view(
            template_name='registration/activation_complete.html'),
        name='registration_activation_complete'),
    # Activation keys get matched by \w+ instead of the more specific
    # [a-fA-F0-9]{40} because a bad activation key should still get to the
    # view; that way it can return a sensible "invalid key" message instead
    # of a confusing 404.
    url(r'^activate/(?P<activation_key>\w+)/$',
        ActivationView.as_view(),
        name='registration_activate'),
    # registration form now in icare4u_front.profiles app
    #    url(r'^register/$',
    #        ICare4uRegistrationView.as_view(),
    #        name='registration_register'),
    url(r'^register/complete/$',
        TemplateView.as_view(
            template_name='registration/registration_complete.html'),
        name='registration_complete'),
    url(r'^register/closed/$',
        TemplateView.as_view(
            template_name='registration/registration_closed.html'),
        name='registration_disallowed'),

    # manually include the auth_urls so that the password_reset can be
    # left out
    # (r'', include('registration.auth_urls')),
    # login overriden at project level - so that Stadlander users cannot
    # login directly
    #    url(r'^login/$',
    #        auth_views.login,
    #        {'template_name': 'registration/login.html'},
    #        name='auth_login'),
    url(r'^logout/$',
        auth_views.logout,
        {'template_name': 'registration/logout.html'},
        name='auth_logout'),
    url(r'^password/change/done/$',
        auth_views.password_change_done,
        name='auth_password_change_done'),

    # password_reset overriden at project level - so that Stadlander users
    # cannot reset their password
    # url(r'^password/reset/$',
    #    auth_views.password_reset,
    #    name='auth_password_reset'),
    url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        name='auth_password_reset_confirm'),
    url(r'^password/reset/complete/$',
        auth_views.password_reset_complete,
        name='auth_password_reset_complete'),
    url(r'^password/reset/done/$',
        auth_views.password_reset_done,
        name='auth_password_reset_done'),
    # password_change overriden at project level - so that Stadlander users
    # cannot change their password
    #    url(r'^password_change/$', auth_views.password_change,
    #        {'password_change_form': CC3PasswordChangeForm},
    #        name="auth_password_change"),
    url(r'^password_reset_confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        {'set_password_form': CC3SetPasswordForm},
        name="auth_password_change_confirm"),
)
