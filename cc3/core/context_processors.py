from django.conf import settings

from cc3.cyclos.models import CC3Profile

from . import utils


def user_cc3_profile(request):
    """Adds cc3 profile (if it exists for a user)."""
    cc3_profile = None
    full_name = ''
    name = ''

    if request.user.is_authenticated():
        try:
            cc3_profile = CC3Profile.viewable.get(user=request.user)
            full_name = cc3_profile.full_name
            name = cc3_profile.name
        except CC3Profile.DoesNotExist:
            pass

    return {
        'user_cc3_profile': cc3_profile,
        'cc3_profile_name': name,
        'cc3_profile_full_name': full_name
    }


def currency_symbol(request):
    return {'currency_symbol': utils.get_currency_symbol()}


def cc3_system_name(request):
    return {
        'cc3_system_name': getattr(settings, "CC3_SYSTEM_NAME", "TradeQoin")
    }


def getvars(request):
    """
    Builds a GET variables string to be used in template links like pagination
    when persistence of the GET vars is needed.
    """
    variables = request.GET.copy()

    if 'page' in variables:
        del variables['page']

    return {
        'getvars': '&{0}'.format(variables.urlencode())
    } if variables else {
        'getvars': ''
    }
