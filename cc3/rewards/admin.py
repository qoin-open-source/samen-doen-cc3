import logging

from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from cc3.cyclos.models import CyclosGroup, User

from .forms import BusinessCauseSettingsModelForm
from .models import BusinessCauseSettings, UserCause, DefaultGoodCause

LOG = logging.getLogger(__name__)


class BusinessCauseSettingsAdmin(admin.ModelAdmin):
    form = BusinessCauseSettingsModelForm
    list_display = ('user', 'reward_percentage', 'transaction_percentage',)
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        cyclos_groups = []

        try:
            cyclos_groups = CyclosGroup.objects.filter(
                name__in=[
                    settings.CYCLOS_CHARITY_MEMBER_GROUP,
                    settings.CYCLOS_BUSINESS_MEMBER_GROUP,
                    settings.CYCLOS_INSTITUTION_MEMBER_GROUP
                ]
            )
            if 'queryset' in kwargs:
                qs = kwargs['queryset'].filter(
                    cc3_profile__cyclos_group__in=cyclos_groups)
            else:
                qs = User.objects.filter(
                    cc3_profile__cyclos_group__in=cyclos_groups)
        except CyclosGroup.DoesNotExist:
            LOG.critical('Charity, Business or Institute Cyclos group '
                         'does not exist.')
        except AttributeError:
            LOG.critical("Django setting CYCLOS_CHARITY_MEMBER_GROUP, "
                         "CYCLOS_BUSINESS_MEMBER_GROUP or "
                         "CYCLOS_INSTITUTION_MEMBER_GROUP not "
                         " defined.")
        finally:
            if not cyclos_groups:
                kwargs['queryset'] = User.objects.none()

        kwargs['queryset'] = qs


#        if db_field.name == 'user':
#            if kwargs.has_key('queryset'):
#                qs = kwargs['queryset'].filter(
#                    cc3_profile__groupset__is_business=True)
#            else:
#                qs = User.objects.filter(
#                    cc3_profile__groupset__is_business=True)
#            kwargs['queryset'] = qs

        return super(
            BusinessCauseSettingsAdmin, self).formfield_for_foreignkey(
                db_field, request, **kwargs)

    class Media:
        js = (
            'js/lib/jquery.min.js',
            'js/enable_percentage.js',
        )


class UserCauseAdmin(admin.ModelAdmin):
    raw_id_fields = ('consumer',)
    list_display = ('consumer', 'cause_name',)

    search_fields = (
        'consumer__email',
        'consumer__first_name',
        'consumer__last_name',
        'cause__email',
        'cause__first_name',
        'cause__last_name',
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Override the default foreignkey list in ``causes`` field to show only
        those profiles who are valid charity causes (the ones who are in the
        'charity' group in Cyclos backend).
        """
        if db_field.name == 'cause':
            cyclos_group = None

            try:
                cyclos_group = CyclosGroup.objects.get(
                    name=settings.CYCLOS_CHARITY_MEMBER_GROUP)
                kwargs['queryset'] = User.objects.filter(
                    cc3_profile__cyclos_group=cyclos_group)
            except CyclosGroup.DoesNotExist:
                LOG.critical('Charity causes Cyclos group does not exist.')
            except AttributeError:
                LOG.critical("Django setting CYCLOS_CHARITY_MEMBER_GROUP not"
                             " defined.")
            finally:
                if not cyclos_group:
                    kwargs['queryset'] = User.objects.none()

        return super(UserCauseAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)


class DefaultGoodCauseForm(forms.ModelForm):
    class Meta:
        model = DefaultGoodCause
        fields = ('community', 'cause')

    def clean(self):
        data = self.cleaned_data
        causes_per_community = DefaultGoodCause.objects.filter(
            community=data['community']).count()
        if causes_per_community > 0:
            raise forms.ValidationError(
                _(u'''You cannot have more than one default good cause per
                community. Please edit the existing Default Good Cause for
                the {0} community''').format(data['community']))

        return data


class DefaultGoodCauseAdmin(admin.ModelAdmin):
    form = DefaultGoodCauseForm
    list_display = ('community', 'cause_name',)

    search_fields = (
        'community__email',
        'community__first_name',
        'community__last_name',
        'cause__email',
        'cause__first_name',
        'cause__last_name',
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Override the default foreignkey list in ``causes`` field to show only
        those profiles who are valid charity causes (the ones who are in the
        'charity' group in Cyclos backend).
        """
        if db_field.name == 'cause':
            cyclos_group = None

            try:
                cyclos_group = CyclosGroup.objects.get(
                    name=settings.CYCLOS_CHARITY_MEMBER_GROUP)
                kwargs['queryset'] = User.objects.filter(
                    cc3_profile__cyclos_group=cyclos_group)
            except CyclosGroup.DoesNotExist:
                LOG.critical('Charity causes Cyclos group does not exist.')
            except AttributeError:
                LOG.critical("Django setting CYCLOS_CHARITY_MEMBER_GROUP not"
                             " defined.")
            finally:
                if not cyclos_group:
                    kwargs['queryset'] = User.objects.none()

        return super(DefaultGoodCauseAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)


admin.site.register(BusinessCauseSettings, BusinessCauseSettingsAdmin)
admin.site.register(UserCause, UserCauseAdmin)
admin.site.register(DefaultGoodCause, DefaultGoodCauseAdmin)
