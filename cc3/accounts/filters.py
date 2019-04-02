# encoding: utf-8
from rest_framework import filters

from cc3.cyclos.models import CC3Profile


class CC3ProfileLocationOrdering(filters.BaseFilterBackend):
    """
    Order results based on the distance between two points.

    Must come last in the filter chain as it returns a RawQuerySet and orders
    the query by location. Multiple ordering parameters are not supported when
    ordering by location.
    """
    def get_location(self, request):
        latitude = request.QUERY_PARAMS.get('latitude')
        longitude = request.QUERY_PARAMS.get('longitude')
        if latitude and longitude:
            return latitude, longitude
        return None, None

    def filter_queryset(self, request, queryset, view):
        latitude, longitude = self.get_location(request)
        distance_km = request.QUERY_PARAMS.get('distance_km')

        if not (latitude and longitude):
            return queryset

        # Now we embark on an inefficient way to honour existing filters and
        # order by location.

        # We want to honour anything else in the filtering chain.
        existing_pks = list(queryset.values_list('pk', flat=True))
        return CC3Profile.viewable.by_distance(
            latitude, longitude, existing_pks=existing_pks,
            distance_threshold=distance_km)
