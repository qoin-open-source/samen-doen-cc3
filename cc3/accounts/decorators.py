from django.core import urlresolvers
from django.http import HttpResponseRedirect
from django.conf import settings

from cc3.cyclos.models import CC3Profile


def must_have_completed_profile(func):
    """
    To stop users continuing if they haven't completed their profile
    """
    def wrapper(request, *args, **kw):
        force_completion = getattr(settings, 'ACCOUNTS_FORCE_COMPLETION', True)
        has_completed_profile = CC3Profile.viewable.has_completed_profile(
            request.user)

        if force_completion and not has_completed_profile:
            return HttpResponseRedirect(
                urlresolvers.reverse('accounts-update-profile'))
        return func(request, *args, **kw)

    return wrapper
