from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag('google_analytics/google_analytics.html')
def google_analytics(_id=None, domain=None):
    if _id is None:
        _id = settings.GOOGLE_ANALYTICS_ID
    if domain is None:
        domain = settings.GOOGLE_ANALYTICS_DOMAIN
    return {
        'GOOGLE_ANALYTICS_ID': _id,
        'GOOGLE_ANALYTICS_DOMAIN': domain
    }

@register.inclusion_tag('google_analytics/google_tag_manager.html')
def google_tag_manager(_id=None, name='dataLayer'):
    if _id is None:
        _id = settings.GOOGLE_TAG_MANAGER_ID

    return {
        'GOOGLE_TAG_MANAGER_ID': _id,
        'GOOGLE_TAG_MANAGER_NAME': name
    }


