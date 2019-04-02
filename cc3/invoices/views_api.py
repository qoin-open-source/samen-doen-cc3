# encoding: utf-8
from rest_framework import permissions, viewsets

from .models import Currency
from .serializers import CurrencySerializer


class CurrenciesAPIViewSet(viewsets.ReadOnlyModelViewSet):
    actions = ['GET']
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = (permissions.AllowAny,)
