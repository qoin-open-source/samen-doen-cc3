# encoding: utf-8
from datetime import datetime, timedelta
import logging

from django import template
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.template.defaultfilters import floatformat
from django.utils import formats
from django.utils.numberformat import format

from cms.models import Page
from cms.templatetags.cms_tags import PageUrl

from cc3.core import utils
from cc3.cyclos.models import CC3Profile

LOG = logging.getLogger(__name__)

register = template.Library()


class SafePageUrl(PageUrl):
    """
    Overrides builtin template tag ``PageUrl`` from Django CMS to just pass any
    exception related to a non existent page. It provides a safe way to use the
    template tag avoiding the risk of critical failures when content is missing
    in the database.
    """
    name = 'safe_page_url'

    def get_context(self, context, page_lookup, lang, site):
        try:
            return super(SafePageUrl, self).get_context(context, page_lookup,
                                                        lang, site)
        except Page.DoesNotExist:
            return {'content': ''}


register.tag(SafePageUrl)


@register.inclusion_tag('cc3/templatetags/_currency.html')
def currency(amount, decimal_places=2):
    return {
        'currency_symbol': utils.get_currency_symbol(),
        'amount': amount,
        'decimal_places': decimal_places,
    }


@register.assignment_tag
def currency_name():
    return getattr(settings, 'CURRENCY_NAME', 'punten')


@register.inclusion_tag('cc3/templatetags/_currency_icon.html')
def currency_icon(amount, decimal_places=2, alert_if_over=None):
    """Display currency value and icon

    If 'alert_if_over' is supplied, the 'alert' flag is set to
    True if 'amount' exceeds this value
    """
    context = {
        'currency_symbol': utils.get_currency_symbol(),
        'amount': amount,
        'decimal_places': decimal_places,
    }
    if alert_if_over is not None:
        try:
            if float(amount) > alert_if_over:
                context['alert'] = True
        except ValueError:
            pass
    return context


@register.inclusion_tag('cc3/templatetags/_large_balance_warning.html',
                        takes_context=True)
def large_balance_warning(context):
    """Display 'You have a large balance' warning, if needed
    """
    rtn = {'large_balance': False}
    large_balance_limit = getattr(settings, 'TRACK_LARGE_BALANCE_LIMIT', None)
    if large_balance_limit is None:
        return rtn

    try:
        user = context['request'].user
    except ObjectDoesNotExist:
        return rtn

    if user and user.is_authenticated():
        try:
            profile = CC3Profile.viewable.get(user=user)
            try:
                balance = profile.current_balance
                if float(balance) > large_balance_limit:
                    return {'large_balance': True,
                            'limit': large_balance_limit,
                            'balance': "%.2f" % balance}
            except ValueError:
                pass
        except CC3Profile.DoesNotExist:
            pass

    return rtn


@register.inclusion_tag('cc3/templatetags/_latest_category_match.html',
                        takes_context=True)
def latest_category_match(context):
    """Display one or more messages about matching wants/offers
    """
    matches = []
    max_age = getattr(settings, 'CATEGORY_MATCHES_ONSCREEN_MAX_AGE', 0)
    if not max_age:
        return {'matches': matches}
    added_since = datetime.now() - timedelta(hours=max_age)

    try:
        user = context['request'].user
    except ObjectDoesNotExist:
        user = None

    if user and user.is_authenticated():
        try:
            profile = CC3Profile.viewable.get(user=user)
            matches = list(
                profile.get_category_matches(added_since=added_since))
        except CC3Profile.DoesNotExist:
            pass

    return {'matches': matches}


@register.filter
def floatformat_localize(value, arg=-1):
    return formats.localize(floatformat(value, arg))


@register.filter
def adimage_set_exists(ad):
    """
    Check if the files exists in the server disc.

    This template filter is useful to check that a thumbnail or a picture
    exists in the media designated directory to prevent ``IOError`` exceptions
    being raised due to a template tag is trying to use an ``AdImage`` which
    holds a file that does not exist.

    :param ad: The ``Ad`` object from which the ``AdImage`` set will be
    extracted.
    :return: ``True`` if the file exists; ``False`` if it doesn't.
    """
    try:
        _ = ad.adimage_set.all()[0]
        return True
    except IOError, e:
        LOG.critical(u'Unable to retrieve AdImage set for Ad {0}: {1}'.format(
            ad.pk, e))
        return False


@register.filter
def lookup(dictionary, key):
    """
    Retrieves a key value in a dictionary passed as a variable to a template
    context.

    Usage: ``{{ dictionary_var|lookup:key }}``

    :param dictionary: The ``dict`` object.
    :param key: The key to retrieve its value from the dict.
    :return: The value of the dictionary key.
    """
    return dictionary.get(key, '')


@register.filter
def last_item(queryset):
    """
    Returns the latest item, by ``pk``, of a given ``QuerySet`` object. This
    should return the latest added object and it is useful for example in the
    case you want to show "latest added image" for an ``Ad``.

    :param queryset: The ``QuerySet`` object to be analyzed.
    :return: The latest object, by ``pk``, of this queryset, if any. ``None``
    otherwise.
    """
    try:
        return queryset.latest('pk')
    except ObjectDoesNotExist:
        return None


@register.filter
def floatdot(value, decimal_pos=4):
    """
    Passed a string representing a decimal number with a comma separator, it
    returns the same decimal number with a dot separator.

    This is useful when the project is using european languages in ``USE_I18N``
    and ``USE_L10N`` and you need to handle decimal numbers in templates to
    process data, like for example happens when you need to process geographic
    coordinates via Javascript in a Dutch or French environment.
    """
    try:
        return format(value, ".", decimal_pos)
    except IndexError:
        # Just fail silently if there is the string is empty.
        pass

floatdot.is_safe = True


@register.filter(name='add_attributes')
def add_attributes(field, css):
    """Add extra atributes (e.g. "class="form-control") to form field

    From http://vanderwijk.info/blog/...
    ...adding-css-classes-formfields-in-django-templates/
    """
    attrs = {}
    definition = css.split(',')

    for d in definition:
        if ':' not in d:
            attrs['class'] = d
        else:
            t, v = d.split(':')
            attrs[t] = v

    return field.as_widget(attrs=attrs)


@register.simple_tag
def get_group_name(ref):
    name = None

    if ref == 'BUSINESS':
        name = 'CYCLOS_BUSINESS_MEMBER_GROUP'
    elif ref == 'INSTITUTION':
        name = 'CYCLOS_INSTITUTION_MEMBER_GROUP'
    elif ref == 'CHARITY':
        name = 'CYCLOS_CHARITY_MEMBER_GROUP'
    elif ref == 'CONSUMER':
        name = 'CYCLOS_CUSTOMER_MEMBER_GROUP'
    elif ref == 'CONSUMER2':
        name = 'CYCLOS_CUSTOMER_MEMBER_GROUP2'

    if name is not None:
        return getattr(settings, name, "")
    else:
        return None


@register.filter
def is_organisaties_group(group):
    if group is not None:
        return group.name == getattr(
            settings, 'CYCLOS_BUSINESS_MEMBER_GROUP', None)
        # "Organisaties"
    else:
        return False


@register.filter
def is_instituties_group(group):
    if group is not None:
        return group.name == getattr(
            settings, 'CYCLOS_INSTITUTION_MEMBER_GROUP', None)
        # "Instituties"
    else:
        return False


@register.filter
def is_goededoelen_group(group):
    if group is not None:
        return group.name == getattr(
            settings, 'CYCLOS_CHARITY_MEMBER_GROUP', None)
        # "Goede Doelen"
    else:
        return False


@register.filter
def is_consumenten_group(group):
    if group is not None:
        return (group.name in getattr(
            settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', []))
        # Consumenten / Consumenten 2
    else:
        return False


# custom template tag that returns the number of active causes
# given an iterable that contains a collection of causes (User)
@register.assignment_tag
def get_active_causes_count(causes):
        return sum(1 for c in causes if c.is_active)
