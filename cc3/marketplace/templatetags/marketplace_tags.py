from django import template
from django.conf import settings

from cc3.marketplace.models import Ad, AdType

register = template.Library()


@register.inclusion_tag('marketplace/latest_offers_wants.html',
                        takes_context=True)
def latest_offers_wants(context, latest_type='offers', number=6): 
    """
    Returns latest offers or wants.
    """
    object_list = Ad.objects.all()
    object_list = object_list.filter(
        status='active',
        adtype=AdType.objects.get(code__iexact=latest_type[0:1]))

    object_list = object_list.order_by('-date_created')

    # Show max 1 ad per user
    # Note that this would work with .distinct('created_by'),
    # however this is only supported on PostgreSQL

    ads = []
    ad_users = []
    for obj in object_list:
        if obj.created_by not in ad_users:
            ads.append(obj)
            ad_users.append(obj.created_by)
        if len(ads) >= number:
            break

    return {'latest_type': latest_type, 'object_list': ads,
            'currency_symbol': settings.CURRENCY_SYMBOL}

