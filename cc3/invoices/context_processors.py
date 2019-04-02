# encoding: utf-8
from cc3.cyclos.models import CC3Profile

from .utils import get_total_outstanding


def total_outstanding(request):
    ctx = {}

    try:
        if request.user.is_authenticated():
            cc3_p = CC3Profile.viewable.get(user=request.user)
            ctx['total_outstanding'] = get_total_outstanding(request.user)
    except CC3Profile.DoesNotExist:
        pass

    return ctx
