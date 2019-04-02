import django_filters

from .models import Ad


class AdFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(name="price", lookup_type='gte')
    max_price = django_filters.NumberFilter(name="price", lookup_type='lte')

    class Meta:
        model = Ad
        fields = ('min_price', 'max_price', 'category', 'adtype',)
