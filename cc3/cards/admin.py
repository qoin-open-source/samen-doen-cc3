import csv
import logging
import os

from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib import admin, messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import RequestContext, render_to_response
from django.utils.translation import ugettext as _

from cc3.core.utils.files import uploaded_file_to_filename
from cc3.cyclos.widgets import (
    CardMachineUserForeignKeyRawIdWidget,
    CardUserForeignKeyRawIdWidget)
from cc3.cyclos.models import CyclosGroup, User
from cc3.excelexport.admin import admin_action_export_xls

from .forms import CSVFileForm, CardNumberForm
from .admin_forms import CardForm
from .models import (
    CardNumber, CardType, Card, Operator, Terminal, CardTransaction,
    CardRegistration, Fulfillment,)

LOG = logging.getLogger(__name__)


class CardNumberAdmin(admin.ModelAdmin):
    readonly_fields = ('creation_date',)
    list_display = ('uid_number', 'number')
    form = CardNumberForm

    def import_csv_view(self, request):
        """
        Imports a CSV file to load multiple ``CardNumber`` objects in the DB.

        The CSV file must consist in a 2 columns format. The first column holds
        the UID number of the cards (hexadecimal) and the second column holds
        the card number (positive integers).
        """
        if request.method == 'POST':
            form = CSVFileForm(request.POST, request.FILES)
            if form.is_valid():
                # Read the CSV file and add the new ``CardNumber``s.
                filename = uploaded_file_to_filename(
                    form.cleaned_data['csv_file'])

                with open(filename, 'rb') as csv_file:
                    csv_reader = csv.reader(csv_file, delimiter=',')
                    for line, row in enumerate(csv_reader, start=1):
                        try:
                            CardNumber.objects.create(
                                uid_number=row[0], number=row[1])
                        except IndexError:
                            pass
                        except ValueError:
                            error_message = u'Invalid values in CSV file, ' \
                                            u'line {0}: {1}'.format(line, row)
                            LOG.error(error_message)
                            messages.add_message(
                                request, messages.ERROR, error_message)

                os.unlink(filename)

                return HttpResponseRedirect(
                    reverse('admin:cards_cardnumber_changelist'))
        else:
            form = CSVFileForm()

        return render_to_response(
            'admin/cards/cardnumber/import_csv.html',
            {'form': form, 'title': _('Import Card numbers from CSV')},
            RequestContext(request))

    def get_urls(self):
        urls = super(CardNumberAdmin, self).get_urls()
        custom_urls = patterns(
            '',
            url(r'^import_csv/$',
                self.admin_site.admin_view(self.import_csv_view),
                name='cards_cardnumber_importcsv'),
        )

        return custom_urls + urls


class CardTypeAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('name',)


class CardAdmin(admin.ModelAdmin):
    form = CardForm
#    ordering = ('uid_number', )# '-creation_date', '-activation_date',)
    actions = [admin_action_export_xls]
    list_display = (
        'card_number',
        'uid_number',
        'email',
        'name',
        'card_type',
    )
    search_fields = (
        'owner__username',
        'owner__first_name',
        'owner__last_name',
        'owner__email',
        'owner__cc3_profile__first_name',
        'owner__cc3_profile__last_name',
        'owner__cc3_profile__business_name',
        'number__uid_number',
        'number__number'
    )
    list_filter = (
        'status',
        'owner__cc3_profile__community',
        'owner__cc3_profile__groupset')
    raw_id_fields = ('owner', )

    def card_number(self, obj):
        return obj.number.number
    card_number.admin_order_field = 'number__number'

    def uid_number(self, obj):
        return obj.number.uid_number
    uid_number.admin_order_field = 'number__uid_number'

    def email(self, obj):
        email_url = reverse(
            'admin:cyclos_cc3profile_change', args=(obj.owner.cc3_profile.pk,))

        return u'<a href="{0}">{1}</a>'.format(email_url, obj.owner.email)
    email.short_description = _(u'Email address')
#    email.admin_order_field = 'owner__email'

    def name(self, obj):
        name_url = reverse(
            'admin:cyclos_cc3profile_change', args=(obj.owner.cc3_profile.pk,))

        return u'<a href="{0}">{1} {2}</a>'.format(
            name_url, obj.owner.cc3_profile.first_name,
            obj.owner.cc3_profile.last_name)
#    name.admin_order_field = 'owner__cc3_profile__last_name'

    email.allow_tags = True
    name.allow_tags = True

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Overrides base ``formfield_for_foreignkey`` method to filter users only
        by their membership to 'business' group.
        """
        # This will act in the case the ``raw_id_fields`` feature is NOT used.
        if db_field.name == 'owner':
            cyclos_groups = None

            try:
                cyclos_groups = CyclosGroup.objects.filter(
                    name__in=settings.CYCLOS_CARD_USER_MEMBER_GROUPS)
                kwargs['queryset'] = User.objects.filter(
                    cc3_profile__cyclos_group__in=cyclos_groups)
            except AttributeError:
                LOG.critical(
                    "Django setting CYCLOS_CARD_USER_MEMBER_GROUPS "
                    "not defined.")
            finally:
                if not cyclos_groups:
                    kwargs['queryset'] = User.objects.none()
                    LOG.critical('Card Machine Cyclos groups do not exist.')

        # This acts in the case we are using ``raw_id_feature``.
        db = kwargs.get('using')

        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = CardUserForeignKeyRawIdWidget(
                db_field.rel, self.admin_site, using=db)

        return db_field.formfield(**kwargs)


class TerminalAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('name', 'business', 'icc_id', 'removed_date', 'comments')
    readonly_fields = ('last_seen_date',)
    raw_id_fields = ('business',)
    ordering = ('name',)

    def get_cardmachineuser_rawid_widget(self, db_field, db):
        """
        Split out from formfield_for_foreignkey() so overriding is simpler
        """
        return CardMachineUserForeignKeyRawIdWidget(
            db_field.rel, self.admin_site, using=db)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Overrides base ``formfield_for_foreignkey`` method to filter users only
        by their membership to 'business' group.
        """
#        LOG.info("in base ff_fk: db_field={0}".format(db_field.name))
#        LOG.info("kwargs:{0}".format(kwargs))
        # This will act in the case the ``raw_id_fields`` feature is NOT used.
        if db_field.name == 'business':
            cyclos_groups = None

            try:
                cyclos_groups = CyclosGroup.objects.filter(
                    name__in=settings.CYCLOS_CARD_MACHINE_MEMBER_GROUPS)
                kwargs['queryset'] = User.objects.filter(
                    cc3_profile__cyclos_group__in=cyclos_groups)
            except AttributeError:
                LOG.critical(
                    "Django setting CYCLOS_CARD_MACHINE_MEMBER_GROUPS "
                    "not defined.")
            finally:
                if not cyclos_groups:
                    kwargs['queryset'] = User.objects.none()
                    LOG.critical('Card Machine Cyclos groups do not exist.')

        # This acts in the case we are using ``raw_id_feature``.
        db = kwargs.get('using')

        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = self.get_cardmachineuser_rawid_widget(
                db_field, db)

        return db_field.formfield(**kwargs)


class OperatorAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('name', 'business')
    readonly_fields = ('last_login_date', 'creation_date')
    raw_id_fields = ('business',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Overrides base ``formfield_for_foreignkey`` method to filter users only
        by their membership to 'business' group.
        """
        # This will act in the case the ``raw_id_fields`` feature is NOT used.
        if db_field.name == 'business':
            cyclos_groups = None

            try:
                cyclos_groups = CyclosGroup.objects.filter(
                    name__in=settings.CYCLOS_CARD_MACHINE_MEMBER_GROUPS)
                kwargs['queryset'] = User.objects.filter(
                    cc3_profile__cyclos_group__in=cyclos_groups)
            except AttributeError:
                LOG.critical(
                    "Django setting CYCLOS_CARD_MACHINE_MEMBER_GROUPS "
                    "not defined.")
            finally:
                if not cyclos_groups:
                    kwargs['queryset'] = User.objects.none()
                    LOG.critical('Card Machine Cyclos groups do not exist.')

        # This acts in the case we are using ``raw_id_feature``.
        db = kwargs.get('using')

        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = CardMachineUserForeignKeyRawIdWidget(
                db_field.rel, self.admin_site, using=db)

        return db_field.formfield(**kwargs)


class CardTransactionAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = (
        'amount', 'date_created', 'sender', 'receiver', 'card', 'description')
    search_fields = (
        'sender__username',
        'sender__email',
        'sender__first_name',
        'sender__last_name',
        'receiver__username',
        'receiver__email',
        'receiver__first_name',
        'receiver__last_name',
        'description')
    raw_id_fields = ('sender', 'receiver', 'operator', 'terminal', 'card')


class CardRegistrationAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('owner', 'creation_date', 'registration_choice')
    list_filter = ('registration_choice', 'creation_date')

from datetime import date


class FulfillmentAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('profile', 'card_registration', 'status',)
    list_editable = ('status',)
    raw_id_fields = ('profile',)


admin.site.register(CardNumber, CardNumberAdmin)
admin.site.register(CardType, CardTypeAdmin)
admin.site.register(Card, CardAdmin)
admin.site.register(Terminal, TerminalAdmin)
admin.site.register(Operator, OperatorAdmin)
admin.site.register(CardRegistration, CardRegistrationAdmin)
admin.site.register(CardTransaction, CardTransactionAdmin)
admin.site.register(Fulfillment, FulfillmentAdmin)
