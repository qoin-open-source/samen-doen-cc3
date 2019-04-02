import logging

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.utils.translation import ugettext as _

from adminsortable.admin import SortableAdmin
from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.widgets import ImageClearableFileInput

from cc3.cyclos import backends
from cc3.cyclos.models import (
    BusinessUserProxyModel, CyclosGroup, CC3Profile, CC3Community,
    CommunityMessage, CommunityRegistrationCode, StatusMessage,
    StatusMessageTranslation, StatusMessageAppearance, UserStatus,
    StatusMessageLevel, User, CommunityAdmin, CyclosGroupSet, CyclosChannel,
    CyclosAccount, CardMachineUserProxyModel,)
from cc3.cyclos.models.account import (
    InstitutionUserProxyModel, CharityUserProxyModel, CardUserProxyModel, FulfillmentProfileProxyModel)
from cc3.excelexport.admin import admin_action_export_xls

LOG = logging.getLogger(__name__)


def admin_action_deactivate_users(modeladmin, request, queryset):
    """
    Django admin interface action to deactivate selected profiles.

    Technically, a 'deactivated' profile is moved into the 'disabled' Cyclos
    group. In Django level, the ``User.is_active`` field is also turned to
    ``False`` status.
    """
    for profile in queryset:
        profile.user.is_active = False
        profile.user.save()

    messages.success(
        request,
        _('{0} profiles successfully deactivated'.format(len(queryset))))


class CommunityCodeInline(admin.TabularInline):
    model = CommunityRegistrationCode
    extra = 1


class CC3CommunityAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('title', 'country', 'code',)
    search_fields = ('title', 'country', 'code',)
    list_filter = ('title', 'country', )
    filter_horizontal = ['groupsets']

    inlines = [CommunityCodeInline]

    fieldsets = (
        (None, {
            'fields': (
                'title', 'country', 'groupsets', 'community_view', 'code',
                'newreg_notify_cadmin', 'profilecomplete_notify_cadmin',
                'transcomplete_notify_cadmin',
                'negative_balance_warning_buffer',
                'negative_balance_collect_after',
                'newcampaign_notify_members')
        }),
        (_('Good Causes Donations: Set percentage rate'), {
            'fields': (
                'default_donation_percent', 'min_donation_percent',
                'max_donation_percent'),
                'description': _(
                    "Note that these percentages may be overridden by "
                    "Institutional users when using the bulk-upload reward "
                    "feature.")
        }),
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "administrator":
            kwargs["queryset"] = User.objects.filter(cc3_profile__isnull=True)
        return super(CC3CommunityAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)


class CC3ProfileAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = (
        'user',
        'first_name',
        'last_name',
        'email',
        'slug',
        'business_name',
        'community',
        'groupset',
    )
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'business_name',
        # 'user__card_set__number__number' conditionally added in __init__
    ]
    list_filter = ('business_name', 'community')
    filter_horizontal = ('categories', 'want_categories')

    prepopulated_fields = {"slug": ("business_name",)}

    raw_id_fields = ('user',)

    formfield_overrides = {
        ThumbnailerImageField: {'widget': ImageClearableFileInput}
    }

    def __init__(self, *args, **kwargs):
        if 'cc3.cards' in settings.INSTALLED_APPS:
            self.search_fields.append('user__card_set__number__number')
        super(CC3ProfileAdmin, self).__init__(*args, **kwargs)

    def email(self, obj):
        return obj.user.email


class CyclosGroupInline(admin.TabularInline):
    model = CyclosGroupSet.groups.through
    extra = 1


class CyclosGroupAdmin(admin.ModelAdmin):
    inlines = [CyclosGroupInline]
    list_display = [
        '__unicode__', 'id', 'groupsets_display', 'communities_display',
        'initial', 'trial', 'full', 'paid', 'inactive',
       # 'create_monthly_invoice', 'create_activation_invoice'
    ]
    filter_horizontal = [
        'initial_products',
    ]
    exclude = [
        'create_monthly_invoice', 'create_activation_invoice',
        'invoice_currency', 'invoice_user', 'invoice_day_otm',
        'invoice_monthly_amount', 'invoice_monthly_description',
        'invoice_activation_amount', 'invoice_activation_description',
    ]

    def sync_groups(self, request, queryset):

        django_groups = {}  # TODO: should this use queryset?
        for group in CyclosGroup.objects.all():
            django_groups[group.id] = group

        # TODO: rationalise in the backend
        cyclos_groups = backends.get_backend().members.listManagedGroups()
        for cyclos_group in cyclos_groups:
            django_group = django_groups.get(cyclos_group.id)

            if django_group:  # check if it exists
                if not django_group.name == cyclos_group.name:
                    self.message_user(
                        request, 'Updated name django {0}, cyclos '
                                 '{1}\n'.format(django_group, cyclos_group))
                    django_group.name = cyclos_group.name
                    django_group.save()

                # delete from list if it does
                del(django_groups[cyclos_group.id])

            else:  # create if not
                self.message_user(request, 'Creating new group {0}\n'.format(
                    cyclos_group.name))
                CyclosGroup.objects.create(
                    pk=cyclos_group.id, name=cyclos_group.name)

        # list any that are missing in cyclos
        for django_group in django_groups:
            self.message_user(request, 'Group {0} no longer in cyclos'.format(
                django_group, level=messages.WARNING))

        self.message_user(request, "Groups synchronised")

    sync_groups.short_description = "Synchronise groups with Cyclos"

    actions = [sync_groups, admin_action_export_xls]


class CyclosGroupSetAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    filter_horizontal = ['groups']
    list_display = (
        '__unicode__', 'groups_display', 'communities_display', 'is_visible',
        'may_add_ads', 'may_view_invoices', 'is_business')


class StatusMessageTranslationInline(admin.TabularInline):
    model = StatusMessageTranslation
    extra = len(settings.LANGUAGES)
    max_num = len(settings.LANGUAGES)


class StatusMessageAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = (
        'user_status',
        'title',
        'message',
        'link',
        'status_message_level',
        'appearance_limit'
    )
    inlines = [StatusMessageTranslationInline]


class UserStatusAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('code', 'description')


class StatusMessageAppearanceAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('message', 'user', 'count')


class CommunityAdminAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('user', 'community')


class CommunityAdminInline(admin.TabularInline):
    model = CommunityAdmin


class UserAdmin(AuthUserAdmin):
    inlines = [CommunityAdminInline]


class BusinessUserAdmin(admin.ModelAdmin):
    """
    Django admin interface to show only those ``cyclos.User``s who are business
    profiles.
    """
    list_display = ('username', 'email', 'first_name', 'last_name')

    def get_queryset(self, request):
        group = getattr(settings, 'CYCLOS_BUSINESS_MEMBER_GROUP', None)
        if group:
            try:
                cyclos_group = CyclosGroup.objects.get(name=group)

                return User.objects.filter(
                    cc3_profile__cyclos_group=cyclos_group)
            except CyclosGroup.DoesNotExist:
                LOG.critical(
                    "Cyclos group '{0}' does not exist".format(group))

        # Missing setting. cannot filter users per group. Return all of them.
        LOG.critical(
            "'CYCLOS_BUSINESS_MEMBER_GROUP' setting not defined")

        return User.objects.all()


class InstitutionUserAdmin(admin.ModelAdmin):
    """
    Django admin interface to show only those ``cyclos.User``s who are business
    profiles.
    """
    list_display = ('username', 'email', 'first_name', 'last_name')

    def get_queryset(self, request):
        group = getattr(settings, 'CYCLOS_INSTITUTION_MEMBER_GROUP', None)
        if group:
            try:
                cyclos_group = CyclosGroup.objects.get(name=group)

                return User.objects.filter(
                    cc3_profile__cyclos_group=cyclos_group)
            except CyclosGroup.DoesNotExist:
                LOG.critical(
                    "Cyclos group '{0}' does not exist".format(group))

        # Missing setting. cannot filter users per group. Return all of them.
        LOG.critical(
            "'CYCLOS_INSTITUTION_MEMBER_GROUP' setting not defined")

        return User.objects.all()


class CharityUserAdmin(admin.ModelAdmin):
    """
    Django admin interface to show only those ``cyclos.User``s who are charity
    profiles.
    """
    list_display = ('username', 'email', 'first_name', 'last_name')

    def get_queryset(self, request):
        group = getattr(settings, 'CYCLOS_CHARITY_MEMBER_GROUP', None)
        if group:
            try:
                cyclos_group = CyclosGroup.objects.get(name=group)

                return User.objects.filter(
                    cc3_profile__cyclos_group=cyclos_group)
            except CyclosGroup.DoesNotExist:
                LOG.critical(
                    "Cyclos group '{0}' does not exist".format(group))

        # Missing setting. cannot filter users per group. Return all of them.
        LOG.critical(
            "'CYCLOS_CHARITY_MEMBER_GROUP' setting not defined")

        return User.objects.all()


class CardUserAdmin(admin.ModelAdmin):
    """
    Django admin interface to show only those ``cyclos.User``s who can use cards
    at card machines (aka terminals).
    """
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_queryset(self, request):
        groups = getattr(settings, 'CYCLOS_CARD_USER_MEMBER_GROUPS', None)
        if groups:
            try:
                cyclos_groups = CyclosGroup.objects.filter(name__in=groups)

                return User.objects.filter(
                    cc3_profile__cyclos_group__in=cyclos_groups)
            except CyclosGroup.DoesNotExist:
                LOG.critical(
                    "Cyclos groups '{0}' do not exist".format(groups))

        # Missing setting. cannot filter users per group. Return all of them.
        LOG.critical(
            "'CYCLOS_CARD_USER_MEMBER_GROUPS' setting not defined")

        return User.objects.all()


class FulfillmentProfileAdmin(admin.ModelAdmin):
    list_display = ('userid', 'email', 'first_name', 'tussenvoegsel', 'last_name', 'business_name')
    search_fields = ('user__username', 'user__email', 'first_name', 'last_name', 'business_name')

    ordering = ['user__username', ]

    def email(self, obj):
        return obj.user.email

    def userid(self, obj):
        return obj.user.id

    def tussenvoegsel(self, obj):
        return obj.userprofile.tussenvoegsel

    email.admin_order_field = 'user__email'
    email.short_description = _("Email address")
    userid.short_description = _(u"User ID")

    def get_queryset(self, request):
        groupsets = (
            getattr(settings, 'CYCLOS_CARD_USER_MEMBER_GROUPS', None),
            getattr(settings, 'CYCLOS_CHARITY_MEMBER_GROUP', None),
        )
        groups = [group for groupset in groupsets if not isinstance(groupset, (str, unicode)) for group in groupset]

        if groups:
            try:
                cyclos_groups = CyclosGroup.objects.filter(name__in=groups)

                return CC3Profile.objects.filter(
                    cyclos_group__in=cyclos_groups, user__is_active=True)
            except CyclosGroup.DoesNotExist:
                LOG.critical(
                    "Cyclos groups '{0}' do not exist".format(groups))

        # Missing setting. cannot filter users per group. Return all of them.
        LOG.critical(
            "'CYCLOS_CARD_USER_MEMBER_GROUPS' setting not defined")

        return CC3Profile.objects.filter(user__is_active=True)


class CardMachineUserAdmin(admin.ModelAdmin):
    """
    Django admin interface to show only those ``cyclos.User``s who can operate
    card machines (aka terminals).
    """
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_queryset(self, request):
        groups = getattr(settings, 'CYCLOS_CARD_MACHINE_MEMBER_GROUPS', None)
        if groups:
            try:
                cyclos_groups = CyclosGroup.objects.filter(name__in=groups)

                return User.objects.filter(
                    cc3_profile__cyclos_group__in=cyclos_groups)
            except CyclosGroup.DoesNotExist:
                LOG.critical(
                    "Cyclos groups '{0}' do not exist".format(groups))

        # Missing setting. cannot filter users per group. Return all of them.
        LOG.critical(
            "'CYCLOS_CARD_MACHINE_MEMBER_GROUPS' setting not defined")

        return User.objects.all()


class CommunityMessageAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('__unicode__', 'plugin', 'community', 'body')


class CyclosChannelAdmin(SortableAdmin):
    actions = [admin_action_export_xls]
    list_display = ('display_name', 'internal_name', 'is_web_channel')


admin.site.register(CC3Profile, CC3ProfileAdmin)
admin.site.register(CC3Community, CC3CommunityAdmin)
admin.site.register(CommunityMessage, CommunityMessageAdmin)
admin.site.register(CyclosGroup, CyclosGroupAdmin)
admin.site.register(CyclosGroupSet, CyclosGroupSetAdmin)
admin.site.register(StatusMessage, StatusMessageAdmin)
admin.site.register(StatusMessageAppearance, StatusMessageAppearanceAdmin)
admin.site.register(UserStatus, UserStatusAdmin)
admin.site.register(StatusMessageLevel)
admin.site.register(CommunityAdmin, CommunityAdminAdmin)
admin.site.register(CyclosChannel, CyclosChannelAdmin)
admin.site.register(CyclosAccount)
admin.site.register(CommunityRegistrationCode)

admin.site.register(User, UserAdmin)
admin.site.register(BusinessUserProxyModel, BusinessUserAdmin)
admin.site.register(InstitutionUserProxyModel, InstitutionUserAdmin)
admin.site.register(CharityUserProxyModel, CharityUserAdmin)
admin.site.register(CardMachineUserProxyModel, CardMachineUserAdmin)
admin.site.register(CardUserProxyModel, CardUserAdmin)
admin.site.register(FulfillmentProfileProxyModel, FulfillmentProfileAdmin)
