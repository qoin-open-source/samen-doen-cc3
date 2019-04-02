from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist

from adminsortable.admin import SortableAdmin

from cc3.excelexport.admin import admin_action_export_xls

from .models import Category, CategoryTranslation, Transaction


class CategoryTranslationInline(admin.TabularInline):
    model = CategoryTranslation
    extra = len(settings.LANGUAGES)
    max_num = len(settings.LANGUAGES)


class CategoryAdmin(SortableAdmin):
    actions = [admin_action_export_xls]
    list_display = ('title', 'parent', 'active')
    inlines = [CategoryTranslationInline]


class TransactionAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = (
        'amount',
        'date_created',
        'sender_email',
        'receiver_email',
        'description'
    )
    search_fields = (
        'sender__username',
        'sender__email',
        'sender__first_name',
        'sender__last_name',
        'receiver__username',
        'receiver__email',
        'receiver__first_name',
        'receiver__last_name',
        'cardtransaction__description',
        'adpaymenttransaction__title'
    )
    list_filter = (
        'sender__cc3_profile__community', 'sender__cc3_profile__groupset')
    raw_id_fields = ('sender', 'receiver',)
    date_hierarchy = 'date_created'

    def sender_email(self, obj):
        return obj.sender.email

    def receiver_email(self, obj):
        return obj.receiver.email

    def description(self, obj):
        try:
            # The transaction was done by card.
            return obj.cardtransaction.description
        except ObjectDoesNotExist:
            # The transaction was done in the web site.
            return obj.adpaymenttransaction.title


admin.site.register(Category, CategoryAdmin)
admin.site.register(Transaction, TransactionAdmin)
