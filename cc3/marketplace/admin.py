from django.conf import settings
from django.contrib import admin
from django import forms
from django.utils.translation import ugettext_lazy as _

from adminsortable.admin import SortableAdmin

from cc3.cyclos.models import CC3Profile
from cc3.excelexport.admin import admin_action_export_xls

from .models import (
    AdImage, Ad, AdType, AdPricingOption, AdPricingOptionTranslation,
    AdPaymentTransaction, Campaign, CampaignCategory,
    CampaignCategoryTranslation, CampaignParticipant)


class AdImageAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]


class AdAdminForm(forms.ModelForm):
    model = Ad

    def clean(self):
        cd = self.cleaned_data
        if (not cd.get('price', None) and not cd.get('price_option', None)) or\
           (cd.get('price', None) and cd.get('price_option', None)):
            raise forms.ValidationError(
                _("Either a price or a price option is required."))
        return cd


class AdAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = (
        'title', 'adtype', 'description', 'price', 'views', 'created_by_email',
        'date_created',
    )
    filter_horizontal = ['category']
    form = AdAdminForm


class AdPricingOptionTranslationInline(admin.TabularInline):
    model = AdPricingOptionTranslation
    extra = len(settings.LANGUAGES)
    max_num = len(settings.LANGUAGES)


class AdPricingOptionAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('title',)
    inlines = [AdPricingOptionTranslationInline]


class AdPaymentTransactionAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = (
        'title', 'receiver_business_name', 'sender_business_name', 'amount',
        'date_created', 'split_payment_total_amount',
    )
    date_hierarchy = 'date_created'
    search_fields = (
        'title', 'sender__cc3_profile__business_name',
        'receiver__cc3_profile__business_name',
    )
    readonly_fields = ('date_created',)

    def receiver_business_name(self, obj):
        try:
            return obj.receiver.cc3_profile.business_name
        except CC3Profile.DoesNotExist:
            return

    def sender_business_name(self, obj):
        try:
            return obj.sender.cc3_profile.business_name
        except CC3Profile.DoesNotExist:
            return


class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'description', 'start_date', 'status', 'max_participants'
    )
    filter_horizontal = ['categories']


class CampaignCategoryTranslationInline(admin.TabularInline):
    model = CampaignCategoryTranslation
    extra = len(settings.LANGUAGES)
    max_num = len(settings.LANGUAGES)


class CampaignCategoryAdmin(SortableAdmin):
    actions = [admin_action_export_xls]
    list_display = ('title', 'parent', 'active')
    inlines = [CampaignCategoryTranslationInline]


class CampaignParticipantAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'profile')


admin.site.register(AdImage, AdImageAdmin)
admin.site.register(AdPricingOption, AdPricingOptionAdmin)
admin.site.register(Ad, AdAdmin)
admin.site.register(AdType)
admin.site.register(AdPaymentTransaction, AdPaymentTransactionAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(CampaignCategory, CampaignCategoryAdmin)
admin.site.register(CampaignParticipant, CampaignParticipantAdmin)
