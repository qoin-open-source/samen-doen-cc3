# encoding: utf-8
from django.contrib import admin

from .models import Currency, CurrencyPair


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'iso_code', 'symbol', 'cyclos_symbol', 'can_be_primary')

class CurrencyPairAdmin(admin.ModelAdmin):
    list_display = ('base', 'counter', 'symbol', 'rate', 'last_updated')

admin.site.register(Currency, CurrencyAdmin)
admin.site.register(CurrencyPair, CurrencyPairAdmin)
