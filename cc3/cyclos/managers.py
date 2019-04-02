from django.db import models
from django.conf import settings

from cc3.cyclos.utils import viewable_user_filter


SYSTEM_USER_IDS = (settings.ANONYMOUS_USER_ID,)


class CC3ProfileManager(models.Manager):
    def has_completed_profile(self, user):
        from cc3.cyclos.models import CC3Profile

        try:
            cc3_profile = CC3Profile.viewable.get(user=user)
        except CC3Profile.DoesNotExist:
            return False

        return cc3_profile.has_completed_profile()

    def is_pending_closure(self, user):
        from cc3.cyclos.models import CC3Profile
        try:
            cc3_profile = CC3Profile.viewable.get(user=user)
        except CC3Profile.DoesNotExist:
            return False

        return cc3_profile.is_pending_closure


class ViewableProfileManager(CC3ProfileManager):
    """
    CC3 Profile manager for profiles that are allowed to be shown in the
    frontend.
    """
    def get_queryset(self):
        # TODO: fix so a super user doesn't get a profile but for now filter
        # out the super users
        return super(ViewableProfileManager, self).get_queryset().\
            exclude(user__is_superuser=True).\
            exclude(user__in=SYSTEM_USER_IDS).\
            filter(viewable_user_filter('user'))

    def get_good_causes_queryset(self):
        # IMPLEMENT at project level
        raise NotImplementedError


class DistanceProfileManager(CC3ProfileManager):

    def by_distance(self, latitude, longitude, existing_pks=None,
                    distance_threshold=None):
        """
        Reurns a RawQuerySet of CC3Profile instances ordered by distance
        (closest first) from a given point. An attribute `distance_km` is added
        to the instances which represents the distance between the two points
        in kilometers calculated by a haversine formula adapted from:
        http://dillieodigital.wordpress.com/2011/06/16/sorting-
        latitudelongitude-positions-by-distance-in-sql/

        `existing_pks` (list) is an optional argument that will allow you (in
            a roundabout way) to include any existing filters.

        Example use:

            trafalgar_square = (51.5081, 0.1281)
            raw_qs = CC3Profile.viewable.by_distance(*trafalgar_square)
            for profile in raw_qs:
                print profile.distance_km
        """
        # We want to honour the filtering of the base get_queryset() function.
        super_pks = set(super(
            DistanceProfileManager, self).get_queryset().values_list(
                'pk', flat=True))

        # If any previous filters has happened (existing_pks) we want to filter
        # for the intersection of the sets of PKs.
        if existing_pks:
            pks = super_pks & set(existing_pks)
        else:
            pks = super_pks

        # This SQL ordering to get NULL distance values last is specific to MySQL.
        distance_where = (
            u"AND distance_km <= {}".format(distance_threshold)
            if distance_threshold else "")
        sql = u"""
            SELECT * FROM (
                SELECT
                    *, (
                        6378 * 2 * ASIN(
                            SQRT(
                                POWER(
                                    SIN((%s - latitude) * pi() / 180 / 2),
                                    2
                                ) + COS(%s * pi() / 180) * COS(latitude * pi() / 180) * POWER(
                                    SIN((%s - longitude) * pi() / 180 / 2),
                                    2
                                )
                            )
                        )
                    ) AS `distance_km`
                FROM
                    `cyclos_cc3profile`) AS qwerty
            WHERE
                `id` IN %s
                {}
            ORDER BY
                -distance_km DESC;
        """.format(distance_where)
        return self.model.objects.raw(sql, params=(
            latitude, latitude, longitude, tuple(pks)))


class CyclosAccountManager(models.Manager):
    def get_for_user(self, user):
        cc3_profile = user.get_profile()
        return self.get_or_create(cc3_profile=cc3_profile)

    def new(self, cc3_profile):
        """
        Create a new account in CC3/Cyclos.
        """
        return self.__get_backend().new(cc3_profile)

    def update(self, cc3_profile):
        return self._get_backend().update(cc3_profile)
