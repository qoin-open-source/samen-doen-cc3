from itertools import islice, chain
import os

from django.conf import settings

from cc3.core.utils import get_image_filename


def get_ad_image_filename(instance, filename):
    """
    Where instance is an 'AdImage'.

    NB, not used directly by model ImageField, even though it's specified.
    Need to use the 'upload_to' ImageField attribute in the form instead
    """
    return get_image_filename(instance.ad, filename, folder_name='ad_image')


def get_campaign_image_filename(instance, filename):
    return os.path.join('campaign_images', '{0}_{1}'.format(
        instance.id, filename))


class QuerySetChain(object):
    """
    Chains multiple subquerysets (possibly of different models) and behaves as
    one queryset.  Supports minimal methods needed for use with
    django.core.paginator.
    """
    def __init__(self, *subquerysets):
        self.querysets = subquerysets

    def count(self):
        """
        Performs a .count() for all subquerysets and returns the number of
        records as an integer.
        """
        return sum(qs.count() for qs in self.querysets)

    def _clone(self):
        "Returns a clone of this queryset chain"
        return self.__class__(*self.querysets)

    def _all(self):
        "Iterates records in all subquerysets"
        return chain(*self.querysets)

    def __getitem__(self, ndx):
        """
        Retrieves an item or slice from the chained set of results from all
        subquerysets.
        """
        if type(ndx) is slice:
            return list(islice(self._all(), ndx.start, ndx.stop, ndx.step or 1))
        else:
            return islice(self._all(), ndx, ndx+1).next()

    def __len__(self):
        """
        :return:sum of length of chained querysets
        """
        return sum([len(qs) for qs in self.querysets])

    def values_list(self, *args, **kwargs):
        "Note: doesn't return a ValueQuerySet, so no further filtering etc. is possible"
        res = []
        for qs in self.querysets:
            res.extend(qs.values_list(*args, **kwargs))
        return res

def user_can_own_campaigns(user):
    owner_groups = getattr(settings, 'CYCLOS_CAMPAIGN_OWNER_GROUPS', ())
    cc3_profile = user.get_cc3_profile()
    if (cc3_profile and cc3_profile.cyclos_group.name in owner_groups):
        return True
    return False

def user_can_join_campaigns(user):
    subscriber_groups = getattr(settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', ())
    cc3_profile = user.get_cc3_profile()
    if (cc3_profile and cc3_profile.cyclos_group.name in subscriber_groups):
        return True
    return False
