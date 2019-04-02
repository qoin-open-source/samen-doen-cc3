from decimal import Decimal
from datetime import date

from cc3.accounts.utils import get_euros_earned_and_redeemed
from dateutil.relativedelta import relativedelta
import logging
from xml.parsers.expat import ExpatError

from django.conf import settings
from django.contrib.auth import user_logged_in
from django.contrib.auth.models import User as AuthUser
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import IntegrityError, models
from django.db.models.fields import IntegerField
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.dispatch import Signal
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.formats import number_format
from django.utils.timezone import now as datetime_now
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils import translation

from django_countries.fields import CountryField
from easy_thumbnails.fields import ThumbnailerImageField

from geopy.exc import GeocoderServiceError
from geopy.geocoders import GoogleV3 as geocoder

from cc3.core.models import Category, TrackedProfileCategory
from cc3.cyclos.common import TransactionException
from .group import CyclosGroup
from cc3.mail.models import (
    MAIL_TYPE_NEW_REGISTRATION, MAIL_TYPE_PROFILE_COMPLETED,
    MAIL_TYPE_NEGATIVE_BALANCE_USER, MAIL_TYPE_NEGATIVE_BALANCE_ADMINS,
    MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_USER,
    MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_ADMINS,
    MAIL_TYPE_LARGE_BALANCE_USER, MAIL_TYPE_LARGE_BALANCE_ADMINS,
    MAIL_TYPE_MATCHING_CATEGORIES, MAIL_TYPE_UPDATED_CATEGORIES,
    )
from cc3.mail.utils import send_mail_to
from cc3.marketplace.common import AD_STATUS_ACTIVE
from cc3.cyclos.services import (
    AccountNotFoundException, MemberNotFoundException)
from cc3.cyclos.utils import mail_community_admins
from cc3.billing.common import BILLING_PERIOD_YEARLY, BILLING_PERIOD_MONTHLY
from .. import backends
from ..managers import (
    CyclosAccountManager, ViewableProfileManager, DistanceProfileManager)
from ..utils import get_profile_picture_filename

import datetime
from django.utils import timezone
import pytz

# TODO: get from settings, with defaults here, if none defined?
SYSTEM_USER_IDS = (
    settings.ANONYMOUS_USER_ID,
    settings.CYCLOS_BANK_USER_ID,
    settings.CYCLOS_FONDS_USER_ID
)

LOG = logging.getLogger('cc3.cyclos.account')

get_fullname_signal = Signal(providing_args=["instance", ])
account_closed_signal = Signal(providing_args=["instance", ])


class User(AuthUser):
    class Meta:
        proxy = True
        app_label = 'cyclos'
#        auto_created = True

    __original_is_active = None

    def get_profile(self):
        """
        Returns system-specific profile for this user.

        Based on code from pre Django deprecating get_profile from the
        User model

        See:
         - https://github.com/django/django/blob/1.5.12/django/contrib/auth/models.py
        """

        if not hasattr(self, '_profile_cache'):
            from django.conf import settings

            app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
            model = models.get_model(app_label, model_name)
            self._profile_cache = model._default_manager.using(
                self._state.db).get(user__id__exact=self.id)
            self._profile_cache.user = self

        return self._profile_cache

    def get_cc3_profile(self):  # TODO: this is ripe for caching
        try:
            return self.cc3_profile
        except CC3Profile.DoesNotExist:
            return None

    def get_community(self):
        """ Return the community to which this user belongs to. """
        profile = self.get_cc3_profile()
        return profile.community if profile else None

    def get_community_admin(self):
        """ Return the community admin for this user. """
        profile = self.get_cc3_profile()
        if not profile:
            return None

        return profile.community.get_default_administrator()

    def get_admin_community(self):
        """ Return the community this user is administrator for or None. """
        try:
            if self.administrator_of:
                return self.administrator_of.community
        except ObjectDoesNotExist:
            return None

    def is_community_admin(self):
        return self.get_admin_community() is not None

    @property
    def business_name(self):
        try:
            return self.cc3_profile.business_name
        except CC3Profile.DoesNotExist:
            return self.get_full_name()

    @property
    def first_activated(self):
        try:
            user_activate_status = UserStatusChangeHistory.objects.filter(
                user=self,
                activate=True
            ).order_by('timestamp')
            return user_activate_status[0].timestamp
        except IndexError:
            pass

        return

    @property
    def last_deactivated(self):
        try:
            user_activate_status = UserStatusChangeHistory.objects.filter(
                user=self,
                activate=False
            ).order_by('-timestamp')
            return user_activate_status[0].timestamp
        except IndexError:
            pass

        return

    @property
    def good_cause(self):
        try:
            from cc3.rewards.models import UserCause
            user_cause = UserCause.objects.get(consumer=self)
            _good_cause = user_cause.cause.cc3_profile.business_name
        except UserCause.DoesNotExist:
            _good_cause = ''
        return _good_cause

    def __init__(self, *args, **kwargs):
        super(AuthUser, self).__init__(*args, **kwargs)
        self.__original_is_active = self.is_active

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        super(AuthUser, self).save(force_insert, force_update, *args, **kwargs)
        self.__original_is_active = self.is_active

    def is_active_has_changed(self):
        return self.__original_is_active != self.is_active


class UserStatusChangeHistory(models.Model):
    user = models.ForeignKey(AuthUser, related_name='target_user')
    change_author = models.ForeignKey(AuthUser, blank=True, null=True,
                                      related_name='change_author')
    timestamp = models.DateTimeField(default=pytz.timezone(
        timezone.get_default_timezone_name()).localize(
        datetime.datetime(2016, 12, 31, 23, 59, 59)).astimezone(pytz.utc))
    activate = models.BooleanField(default=True)


class BusinessUserProxyModel(User):
    """
    This is a proxy ``models.Model`` class. It is being used to provide a nice
    filter in those ``ModelAdmin``s which require to show ``User``s filtered by
    those who are 'business' users.

    Workarounds the Django design which only allows to register one admin
    interface per model, avoiding raising ``AlreadyRegistered`` exception.
    """
    class Meta:
        proxy = True
        app_label = 'accounts'
        verbose_name = _('User (Business)')
        verbose_name_plural = _('Users (Businesses)')
        # app label causes migrations to be created in the auth app
        managed = False


class InstitutionUserProxyModel(User):
    """
    This is a proxy ``models.Model`` class. It is being used to provide a nice
    filter in those ``ModelAdmin``s which require to show ``User``s filtered by
    those who are 'institute' users.

    Workarounds the Django design which only allows to register one admin
    interface per model, avoiding raising ``AlreadyRegistered`` exception.
    """
    class Meta:
        proxy = True
        app_label = 'accounts'
        verbose_name = _('User (Institution)')
        verbose_name_plural = _('Users (Institutions)')
        # app label causes migrations to be created in the auth app
        managed = False


class CharityUserProxyModel(User):
    """
    This is a proxy ``models.Model`` class. It is being used to provide a nice
    filter in those ``ModelAdmin``s which require to show ``User``s filtered by
    those who are 'charity' users.

    Workarounds the Django design which only allows to register one admin
    interface per model, avoiding raising ``AlreadyRegistered`` exception.
    """
    class Meta:
        proxy = True
        app_label = 'accounts'
        verbose_name = _('User (Charity)')
        verbose_name_plural = _('Users (Charity)')
        # app label causes migrations to be created in the auth app
        managed = False


class CardMachineUserProxyModel(User):
    """
    This is a proxy ``models.Model`` class. It is being used to provide a nice
    filter in those ``ModelAdmin``s which require to show ``User``s filtered by
    those who are 'card machine' users (defined by setting
    CYCLOS_CARD_MACHINE_MEMBER_GROUPS).

    Workarounds the Django design which only allows to register one admin
    interface per model, avoiding raising ``AlreadyRegistered`` exception.
    """
    class Meta:
        proxy = True
        app_label = 'accounts'
        verbose_name = _('User (Card Machine)')
        verbose_name_plural = _('Users (Card Machine)')
        # app label causes migrations to be created in the auth app
        managed = False


class CardUserProxyModel(User):
    """
    This is a proxy ``models.Model`` class. It is being used to provide a nice
    filter in those ``ModelAdmin``s which require to show ``User``s filtered by
    those who are 'card machine' users (defined by setting
    CYCLOS_CARD_USER_MEMBER_GROUPS).

    Workarounds the Django design which only allows to register one admin
    interface per model, avoiding raising ``AlreadyRegistered`` exception.
    """

    class Meta:
        proxy = True
        app_label = 'accounts'
        verbose_name = _('User (Card)')
        verbose_name_plural = _('Users (Card)')
        # app label causes migrations to be created in the auth app
        managed = False


# Monkey patch the User.username field to have a longer max_length to support
# email addresses.
# User._meta.get_field('username').max_length = 75

def password_change_signal(sender, instance, **kwargs):
    """ Set must_reset_password to False if password has been set """
    try:
        user = User.objects.get(username=instance.username)
        if not user.password == instance.password:
            try:
                profile = user.cc3_profile
                profile.must_reset_password = False
                profile.save()
            except CC3Profile.DoesNotExist:
                pass
    except User.DoesNotExist:
        pass

pre_save.connect(password_change_signal, sender=User,
                 dispatch_uid='cyclos.models')


class CC3Profile(models.Model):
    """
    Placeholder for user profiles.
    Originated in Fundament Caire django integration code.
    """

    user = models.OneToOneField(
        User, unique=True, verbose_name=_(u'user'), related_name='cc3_profile')

    first_name = models.CharField(
        _('First name'), max_length=255, blank=True, default='')
    last_name = models.CharField(
        _('Last name'), max_length=255, blank=True, default='')
    business_name = models.CharField(
        _('Business name'), max_length=255, blank=True, default='')
    slug = models.SlugField(max_length=255, blank=True, default='')

    picture = ThumbnailerImageField(
        _('Picture'), upload_to=get_profile_picture_filename, blank=True,
        height_field='picture_height', width_field='picture_width')
    picture_height = models.IntegerField(
        _('Picture height'), blank=True, null=True, editable=False)
    picture_width = models.IntegerField(
        _('Picture width'), blank=True, null=True, editable=False)
    job_title = models.CharField(
        _('Job title'), max_length=255, blank=True, default='')

    country = CountryField(_('Country'))
    city = models.CharField(_('City'), max_length=255, blank=True, default='')
    address = models.CharField(
        _('Address'), max_length=255, blank=True, default='')
    postal_code = models.CharField(
        _('Postal code'), max_length=10, blank=True, default='')
    phone_number = models.CharField(
        _('Phone number'), max_length=255, blank=True, default='')
    mobile_number = models.CharField(
        _('Mobile number'), max_length=255, blank=True, default='')
    company_website = models.URLField(
        _('Company website'), max_length=255, blank=True, default='')
    company_description = models.TextField(
        _('Company description'), blank=True, default='')

    must_reset_password = models.BooleanField(
        _('Must reset password'), default=False)
    is_pending_closure = models.BooleanField(
        _('Is pending closure'), default=False)
    date_closure_requested = models.DateTimeField(
        _('Date closure requested'), blank=True, null=True)
    is_visible = models.BooleanField(_('Is visible'), default=True, help_text=_(
        "Marking as visible shows the profile to be shown on the marketplace"
    ))
    is_approved = models.BooleanField(_('Profile approved'), help_text=_(
        "Approving profile will automatically make it visible; unapproving "
        "will make it invisible"),
        default=True)
    has_received_activation_invoice = models.BooleanField(
        _('Has received activation invoice'), default=False)
    has_notified_profilecomplete = models.BooleanField(
        _('Has notified profile complete'), default=False)

    categories = models.ManyToManyField(
        'core.Category', blank=True)  # ='offer categories'
    want_categories = models.ManyToManyField(
        'core.Category', blank=True, related_name="cc3profile_wanting")
    email_category_matches = models.BooleanField(
        _('Notify me of new matches'), default=True,
    )

    email_new_campaigns = models.BooleanField(
        _('Notify me about new activities'), default=True,
    )

    credit_term = models.IntegerField(_('Credit term (months)'),
                                      blank=True, null=True, default=4)
    negative_balance_start_date = models.DateField(
        _('Date balance went negative'), blank=True, null=True)
    negative_balance_warning_sent = models.DateField(
        _('Date negative balance warning was sent'),
        blank=True, null=True)
    negative_balance_collect_sent = models.DateField(
        _('Date negative balance collection email was sent'),
        blank=True, null=True)
    large_balance_start_date = models.DateField(
        _('Date balance exceeded limit'), blank=True, null=True)

    # community - in a specific location / country
    community = models.ForeignKey(
        'cyclos.CC3Community', verbose_name=_(u"Community"),
        blank=True, null=True)
    groupset = models.ForeignKey(
        'cyclos.CyclosGroupSet', blank=True, null=True)
    cyclos_group = models.ForeignKey(
        'cyclos.CyclosGroup', verbose_name=_(u"Cyclos Group"),
        blank=True, null=True)

    web_payments_enabled = models.BooleanField(
        default=True,
        help_text=_("Allow user to make payments in the marketplace"))

    latitude = models.DecimalField(
        null=True,
        blank=True,
        max_digits=17,
        decimal_places=14)

    longitude = models.DecimalField(
        null=True,
        blank=True,
        max_digits=17,
        decimal_places=14)

    map_zoom = models.IntegerField(
        null=True,
        blank=True
    )

    first_login = models.NullBooleanField(
        help_text=_("Is this the first time a user has logged in? "
                    "(Defaults to true in save method)"),
    )
    original_date_joined = models.DateTimeField(
        _(u'Original Date Joined'), blank=True, null=True)

    objects = DistanceProfileManager()
    viewable = ViewableProfileManager()

    class Meta:
        app_label = 'cyclos'
        verbose_name = _(u'profile')
        verbose_name_plural = _(u'profiles')

    def __unicode__(self):
        return u'{0}'.format(self.full_name or str(self.pk))

    def save(self, *args, **kwargs):
        assign_initial_products = False

        if self.pk is None:

            #  self.first_login = True  # Default first login to true

            # New profile: override approval/visibility where necessary -
            # set up proper defaults if not
            if getattr(settings, 'ADMINS_APPROVE_PROFILES', False):
                self.is_approved = False
                self.is_visible = False
            else:
                # if it's group consumenten/consumenten2 then make visible
                # false. Ticket #2702
                if self.cyclos_group and self.cyclos_group.name in getattr(
                        settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', []):
                    self.is_visible = False
                else:
                    self.is_visible = True

            # It's a new record so geocode the postal code
            self.geocode_postal_code()

            # and assign initial products
            assign_initial_products = True

        else:
            # Existing profile: if is_approved has changed, set visibility.
            try:
                old = CC3Profile.objects.get(pk=self.pk)

                if getattr(settings, 'ADMINS_APPROVE_PROFILES', False):
                    if old.is_approved != self.is_approved:
                        self.is_visible = self.is_approved

                lng_to_compare = Decimal("{:.14f}".format(
                    float(self.longitude))) if self.longitude else None
                lat_to_compare = Decimal("{:.14f}".format(
                    float(self.latitude))) if self.latitude else None

                # Geocode the postal code if it's changed and the lng/lat hasn't
                if (old.postal_code != self.postal_code and (
                    old.longitude == lng_to_compare and
                        old.latitude == lat_to_compare)):
                    self.geocode_postal_code()

            except CC3Profile.DoesNotExist:
                # Actually a new profile created with explicit id: don't mess
                # with the flags because the caller has probably set them as
                # wanted.
                pass

        # Call the "real" save() method.
        super(CC3Profile, self).save(*args, **kwargs)

        # auto-assign any Products specified in cyclos_group
        # (have to do this after profile is saved, for id)
        if assign_initial_products and self.cyclos_group:
            for product in self.cyclos_group.initial_products.all():
                product.assign_to_user(self)

    def get_absolute_url(self):
        try:
            return reverse(
                'marketplace-business-profile',
                args=[self.slug])
        except NoReverseMatch:
            LOG.error(u'Failed to reverse absolute URL for CC3Profile '
                      u'{0}'.format(self.pk))
            return ''

    @property
    def name(self):
        """
        Returns the complete name of the profile owner.
        """
        if self.first_name and self.last_name:
            return u"{0} {1}".format(self.first_name, self.last_name)
        else:
            return self.user.email

    @property
    def full_name(self):
        """
        Returns the complete name plus the business name of the profile owner.
        """
        get_fullname_result = get_fullname_signal.send(
            sender=CC3Profile, instance=self)

        for func, fullname in get_fullname_result:
            if fullname:
                return fullname

        if self.first_name and self.last_name and self.business_name:
            return u"{0} {1} ({2})".format(
                self.first_name, self.last_name, self.business_name)
        elif self.first_name and self.last_name:
            return u"{0} {1}".format(self.first_name, self.last_name)
        else:
            # Do not show any full name unless one has been entered (ie profile
            # completed).
            return u''

    @property
    def active_ad_count(self):
        return self.ad_set.filter(status=AD_STATUS_ACTIVE).count

    def get_picture(self):
        """
        In order to allow template to fail gracefully, move exception handling
        up to model
        :return: picture (thumbnailable image) or None
        """
        try:
            if self.picture.file:
                return self.picture
        except ValueError:
            return None
        except IOError:
            return None

    def get_cyclos_group(self):
        """
        Return the ``CyclosGroup`` for this ``CC3Profile`` or ``None``.
        """
        group_id = backends.get_group(self.user.email)
        if self.community:
            groups = self.community.get_groups()
            initial_groups = groups.filter(initial=True, id=group_id)
            if initial_groups:
                return initial_groups[0]
            full_groups = groups.filter(full=True, id=group_id)
            if full_groups:
                return full_groups[0]
        return None

    def sync_cyclos_group(self):
        """
        Updates the ``cyclos_group`` field with the current Cyclos group in the
        Cyclos remote database.
        """
        group = self.get_cyclos_group()
        if group:
            self.cyclos_group = group
            self.save()
            return True
        else:
            LOG.critical(
                "User '{0}' does not belong to any Cyclos group".format(
                    self.user.email))
            return False

    def has_wants(self):
        from cc3.marketplace.models import Ad

        return len(Ad.objects.filter(created_by__slug=self.slug).filter(
            adtype__code__iexact='W')) > 0

    def get_account_number(self):
        """
        Return a string that uniquely identifies this account.

        (PK optionally prefixed with a value dependend on the groupset).
        """
        if not self.groupset:
            return unicode(self.pk)
        return "{0}{1}".format(self.groupset.prefix, self.pk)

    def split_payments_allowed(self):
        """
        Return if this CC3Profile is allowed to make split payments.

        (payments also in Euro's).
        """
        cyclos_group = self.get_cyclos_group()
        if not cyclos_group:
            return False
        return cyclos_group.permit_split_payments_in_euros

    def inter_communities_transactions_allowed(self):
        allowed = getattr(
            settings, 'INTER_COMMUNITIES_TRANSACTIONS', False)

        if not allowed:
            # check for override
            groups_allowed = getattr(
                settings, 'INTER_COMMUNITIES_TRANSACTIONS_MEMBER_GROUPS', [])
            if self.cyclos_group:
                allowed = self.cyclos_group.name in groups_allowed

        return allowed

    def has_full_account(self):
        if getattr(settings, 'CYCLOS_HAS_TRIAL_ACCOUNTS', True):
            group_id = backends.get_group(self.user.email)
            if group_id is None or (self.community and group_id in list(
                    self.community.get_initial_groups().values_list(
                        'id', flat=True))):
                return False
            else:
                return True
        else:
            return True

    def get_simple_account_type(self):
        """ simplified version of get_account_type used in communityadmin """
        if self.has_full_account():
            return _('Free')
        else:
            return _('Paid')

    def get_account_type(self):
        """
        Get whether the account is free or paid
        TODO: I (SW) think David must be relying on the member_group_id being
        the free group, and any others being paid
        I added the check for None, as this was returning Paid account for
        members who hadn't completed their profile yet
        and hadn't actually been created on the Cyclos side.
        """
        if self.has_full_account() or not getattr(
                settings, 'CYCLOS_HAS_TRIAL_ACCOUNTS', True):
            return _('Paid account')
        else:
            account_type_string = \
                u'{0} : <a href="{1}" style="color:white;">' \
                u'{2}</a>'.format(
                    _('Free Account'),
                    reverse('accounts-credit'),
                    _('Upgrade'))

            return account_type_string

    def count_offers(self):
        return self.ad_set.filter(adtype__code='O').count()

    def count_wants(self):
        return self.ad_set.filter(adtype__code='W').count()

    def count_active_ads(self):
        return self.ad_set.filter(status=AD_STATUS_ACTIVE).count()

    def number_member_to_member_transactions(self):
        from cc3.marketplace.models import AdPaymentTransaction
        user = self.user
        return AdPaymentTransaction.objects.filter(
            models.Q(sender=user) | models.Q(receiver=user)).count()

    def total_payments_incoming(self):
        from cc3.marketplace.models import AdPaymentTransaction
        user = self.user
        received = AdPaymentTransaction.objects.filter(
            receiver=user).values_list('amount', flat=True)
        return sum(received)

    def total_payments_outgoing(self):
        from cc3.marketplace.models import AdPaymentTransaction
        user = self.user
        sent = AdPaymentTransaction.objects.filter(
            sender=user).values_list('amount', flat=True)
        return sum(sent)

    def get_transaction_info(self):
        # Get all cyclos transactions and return summary info,
        # as a dict. Current items:
        # - 'total_amounts' = dict, keyed by direction of transfer, of
        # dicts, keyed by transfer_type, holding total amounts
        # - ...
        # Add more as needed
        info = {
            'total_amounts': {
                'sent': {},
                'received': {},
                'unknown': {}
            },
        }
        try:
            transactions = backends.transactions(
                self.user.username)
        except AccountNotFoundException:
            LOG.error(u'Account {0} not found. No transactions '
                      u'shown.'.format(self.user.username))
            return info
        try:
            # check there are transactions to iterate through,
            if transactions and transactions.count():
                for trans in transactions:
                    LOG.info("sender: {0}, recipient: {1}".format(
                        trans.sender, trans.recipient))
                    if trans.sender == self.user.username:
                        direction = 'sent'
                    elif trans.recipient == self.user.username:
                        direction = 'received'
                    else:
                        direction = 'unknown'
                    transfer_type_id = trans.transfer_type_id
                    if info['total_amounts'][direction].has_key(
                            transfer_type_id):
                        info['total_amounts'][direction][transfer_type_id] += \
                            trans.amount
                    else:
                        info['total_amounts'][direction][transfer_type_id] = \
                            trans.amount
        # transaction.count() raises a MemberNotFoundException, if cyclos
        # doesn't know the user
        except MemberNotFoundException:
            LOG.error(u'Account {0} not found. No transactions '
                      u'shown.'.format(self.user.username))
            return info
        LOG.debug(
            "transaction_total_amounts: {0}".format(info['total_amounts']))
        return info

    def euros_earned_and_redeemed(self):
        # Return the total amounts earned and redeemed by this user,
        # converted to euros
        rtn = get_euros_earned_and_redeemed(self.user.username)
        return rtn

    @property
    def current_balance(self):
        status = self.credit_status()
        if status:
            return status.balance
        return '-'

    def current_credit_limit(self):
        status = self.credit_status()
        if status:
            return status.creditLimit
        return None

    def credit_status(self):
        """
        Returns an accountStatus object for this user, with the following
        properties:
        - balance
        - creditLimit
        - upperCreditLimit
        """
        try:
            account_status = backends.get_account_status(self.user.username)
            return account_status.accountStatus
        except AccountNotFoundException:
            LOG.error(u"Cyclos account '{0}' does not exist".format(
                self.user.username))
            return None
        except MemberNotFoundException:
            LOG.error(
                u"Unable to retrieve current balance of Cyclos "
                u"CC3Profile/member '{0}': not found".format(
                    self.user.username))
            return None

    def update_slug(self, override=False):
        """
        Update slug if blank, or override=True
        """
        if (not self.slug or override) and self.business_name:

            business_slug_count = 0
            # TODO - factor this out as it is duplicated in accounts/views.py
            business_slug = slugify(self.business_name)
            test_business_slug = business_slug

            while self.__class__.objects.filter(slug=test_business_slug):
                business_slug_count += 1
                test_business_slug = u"{0}{1}".format(
                    business_slug, business_slug_count)

            self.slug = test_business_slug
            self.save()

    def has_completed_profile(self):
        return self.first_name and self.last_name and self.business_name

    def can_order_card(self):
        """ Overriden at project level - correct Profile super class obtained
        by user.get_profile() """
        return True

    def pays_for_card(self):
        """
        Overriden at project level - correct Profile super class obtained by
        ``user.get_profile()``
        """
        return True

    def track_negative_balance(self, latest_balance):
        """
        If profile's balance has gone positive or negative record the details
        """
        if not getattr(settings, 'TRACK_NEGATIVE_BALANCES', False):
            # do nothing
            return
        if latest_balance >= 0 and self.negative_balance_start_date:
            # balance is no longer negative: clear fields
            LOG.info(u"Negative balance cleared for {0}".format(self.full_name))
            self.negative_balance_start_date = None
            self.negative_balance_warning_sent = None
            self.negative_balance_collect_sent = None
            self.save()
        elif latest_balance < 0 and not self.negative_balance_start_date:
            # balance has gone negative: set fields
            LOG.info(u"Negative balance entered for {0}".format(self.full_name))
            self.negative_balance_start_date = date.today()
            self.save()

    def track_large_balance(self, latest_balance):
        limit = getattr(settings, 'TRACK_LARGE_BALANCE_LIMIT', None)
        if limit is None:
            # do nothing
            return
        if latest_balance > limit and not self.large_balance_start_date:
            # balance has just exceeded limit: send emails and set start_date
            LOG.info(
                u"Large balance limit exceeded for {0}".format(self.full_name))
            self.send_large_balance_emails(latest_balance, limit)
            self.large_balance_start_date = date.today()
            self.save()
        elif latest_balance <= limit and self.large_balance_start_date:
            # balance has dropped below limit, clear the start_date
            LOG.info(u"Large balance cleared for {0}".format(self.full_name))
            self.large_balance_start_date = None
            self.save()

    def get_date_credit_expires(self):
        if self.negative_balance_start_date and self.credit_term:
            return self.negative_balance_start_date + relativedelta(
                months=self.credit_term)
        return None

    def negative_balance_warning_due(self):
        """
        Check whether warning emails to user and admins are due

        i.e. if:
        - TRACK_NEGATIVE_BALANCES is on
        - user's balance is negative
        - warning message has not already been sent, and
        - it is n days or less before the user's credit term expires
          (where n is the community-configured warning buffer)
        """
        if not getattr(settings, 'TRACK_NEGATIVE_BALANCES', False):
            return False
        if self.negative_balance_warning_sent:
            return False
        if not self.negative_balance_start_date:
            return False
        days_before = self.community.negative_balance_warning_buffer
        if days_before is not None:
            warning_due_date = self.get_date_credit_expires() - relativedelta(
                days=days_before)
            if warning_due_date <= date.today():
                return True
        return False

    def negative_balance_collect_due(self):
        """
        Check whether collection emails to user and admins are due

        i.e. if:
        - TRACK_NEGATIVE_BALANCES is on
        - user's balance is negative
        - collect message has not already been sent, and
        - it is n months or more after the user's credit term expires
          (where n is the community-configured collect-after value)
        """
        if not getattr(settings, 'TRACK_NEGATIVE_BALANCES', False):
            return False
        if self.negative_balance_collect_sent:
            return False
        if not self.negative_balance_start_date:
            return False
        months_after = self.community.negative_balance_collect_after
        if months_after is not None:
            collect_due_date = self.get_date_credit_expires() + relativedelta(
                months=months_after)
            if collect_due_date <= date.today():
                return True
        return False

    def send_negative_balance_warning_emails(self):
        """
        Send warning emails to user and admins
        """
        language = translation.get_language()
        context = {
            'name': self.full_name,
            'negative_since': self.negative_balance_start_date,
            'credit_expires': self.get_date_credit_expires(),
            'credit_term': self.credit_term,
            'balance': number_format(self.current_balance, 2),
        }
        # first, to the user
        LOG.info(u"Sending negative balance warning email to {0}". format(
            self.full_name))
        sent = send_mail_to(recipients=(self,),
                            mail_type=MAIL_TYPE_NEGATIVE_BALANCE_USER,
                            language=language,
                            context=context)
        if sent:
            self.negative_balance_warning_sent = date.today()
            self.save()

        # then to admins
        send_mail_to(recipients=self.community.get_administrators(),
                     mail_type=MAIL_TYPE_NEGATIVE_BALANCE_ADMINS,
                     language=language,
                     context=context)

    def send_negative_balance_collect_emails(self):
        """
        Send collection emails to user and admins
        """
        language = translation.get_language()
        context = {
            'name': self.full_name,
            'negative_since': self.negative_balance_start_date,
            'credit_expires': self.get_date_credit_expires(),
            'collection_term': (self.credit_term +
                                self.community.negative_balance_collect_after),
            'balance': number_format(self.current_balance, 2),
        }
        # first, to the user
        LOG.info(u"Sending negative balance collection email to {0}". format(
                 self.full_name))
        sent = send_mail_to(recipients=(self,),
                            mail_type=MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_USER,
                            language=language,
                            context=context)
        if sent:
            self.negative_balance_collect_sent = date.today()
            self.save()

        # then to admins
        send_mail_to(recipients=self.community.get_administrators(),
                     mail_type=MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_ADMINS,
                     language=language,
                     context=context)

    def send_large_balance_emails(self, balance, limit):
        """
        Send warning emails to user and admins
        """
        language = translation.get_language()
        context = {
            'name': self.full_name,
            'balance': number_format(self.current_balance, 2),
            'limit': limit,
        }
        # first, to the user
        LOG.info(u"Sending large balance warning email to {0}". format(
                 self.full_name))

        send_mail_to(recipients=(self,),
                     mail_type=MAIL_TYPE_LARGE_BALANCE_USER,
                     language=language,
                     context=context)
        # then to admins
        send_mail_to(recipients=self.community.get_administrators(),
                     mail_type=MAIL_TYPE_LARGE_BALANCE_ADMINS,
                     language=language,
                     context=context)

    def notify_matching_categories(self, added_since):
        """
        Send emails about matching want and offer categories
        """
        # first check for offers matching my wants:
        my_wants = list(cat.id for cat in self.want_categories.all())
        LOG.debug(u"My wants: {0}".format(my_wants))

        offers_matching_my_wants = TrackedProfileCategory.objects.filter(
            category_type=TrackedProfileCategory.TYPE_OFFER,
            time_added__gt=added_since,
            category_id__in=my_wants
        ).exclude(
            profile=self
        ).all()

        for offer in offers_matching_my_wants:
            LOG.debug(u"New match: {0} is offering {1}".format(
                offer.profile.business_name, offer.category))

        # now check for wants matching my offers:
        my_offers = (cat.id for cat in self.categories.all())
        wants_matching_my_offers = TrackedProfileCategory.objects.filter(
            category_type=TrackedProfileCategory.TYPE_WANT,
            time_added__gt=added_since,
            category_id__in=my_offers
        ).exclude(
            profile=self
        ).all()

        for want in wants_matching_my_offers:
            LOG.debug(u"New match: {0} wants {1}".format(
                want.profile.business_name, want.category))

        if len(offers_matching_my_wants) or len(wants_matching_my_offers):
            # send an email
            language = translation.get_language()
            context = {
                'name': self.full_name,
                'wants_matching_my_offers': wants_matching_my_offers,
                'offers_matching_my_wants': offers_matching_my_wants,
            }
            LOG.info(u"Sending matching Wants/Offers email to {0}". format(
                     self.full_name))

            send_mail_to(recipients=(self,),
                         mail_type=MAIL_TYPE_MATCHING_CATEGORIES,
                         language=language,
                         context=context)

    def handle_updated_categories(self, added_category_ids, max_matches=10):
        """
        Find matching Wants, and store for later use
        """
        matches = []
        # find profiles wanting these categories, most recently added first
        for profile in CC3Profile.viewable.order_by('-user__date_joined').all():
            if not profile == self:
                matching_wants = [cat for cat in profile.want_categories.all()
                                  if cat.id in added_category_ids]
                if matching_wants:
                    matches.append({'profile': profile,
                                    'categories': matching_wants,
                                    })
            if len(matches) >= max_matches:
                break
        if matches:
            # store for use in view
            self._category_matches = matches

    def handle_updated_want_categories(
            self, added_category_ids, max_matches=10):
        """
        Find matching Offers, and store for later use
        """
        matches = []
        # find profiles offering these categories, most recently added first
        for profile in CC3Profile.viewable.order_by('-user__date_joined').all():
            if not profile == self:
                matching_offers = [cat for cat in profile.categories.all()
                                   if cat.id in added_category_ids]
                if matching_offers:
                    matches.append({'profile': profile,
                                    'categories': matching_offers,
                                    })
            if len(matches) >= max_matches:
                break
        if matches:
            # store for use in view
            self._want_category_matches = matches

    def get_html_updated_categories_messages(
            self, message_template="fragments/category_update_message.html"):
        """Return category match messages for display when profile updated

        These are HTML formatted messages, so need to be displayed with
        the |safe filter
        """
        messages = []
        if hasattr(self, '_category_matches'):
            msg = render_to_string(message_template,
                                   {'type': 'want',
                                    'matches': self._category_matches})

            messages.append(msg)
        if hasattr(self, '_want_category_matches'):
            msg = render_to_string(message_template,
                                   {'type': 'offer',
                                    'matches': self._want_category_matches})
            messages.append(msg)
        return messages

    def send_updated_categories_email_if_needed(self):
        """Send email if new categories were added during profile update

        Use current langauge, because this is invoked by the user himself
        """
        category_matches = []
        want_category_matches = []
        if hasattr(self, '_category_matches'):
            category_matches = self._category_matches
        if hasattr(self, '_want_category_matches'):
            want_category_matches = self._want_category_matches

        if category_matches or want_category_matches:
            # send the email
            language = translation.get_language()
            context = {
                'name': self.full_name,
                'wants_matching_my_offers': category_matches,
                'offers_matching_my_wants': want_category_matches,
            }
            LOG.info(u"Sending updated categories email to {0}". format(
                     self.full_name))

            send_mail_to(recipients=(self,),
                         mail_type=MAIL_TYPE_UPDATED_CATEGORIES,
                         language=language, context=context)

    def get_category_matches(self, added_since):
        """
        Return a list of matches for my wants and offers
        """
        matches = []
        my_wants = list(cat.id for cat in self.want_categories.all())
        my_offers = list(cat.id for cat in self.categories.all())
        for possible in TrackedProfileCategory.objects.filter(
            time_added__gt=added_since).exclude(
                profile=self).order_by('-time_added'):
            if possible.category_type == TrackedProfileCategory.TYPE_OFFER:
                if possible.category.id in my_wants:
                    matches.append(possible)
            else:
                if possible.category.id in my_offers:
                    matches.append(possible)
        return matches

    def get_geocode_address(self):
        return str(self.country) + ', ' + self.postal_code

    def geocode_postal_code(self):
        """
        Geocodes given address via google geocode API.
        """
        try:
            # Run the geocoder
            location = geocoder().geocode(self.get_geocode_address())

            # If it works then assign the result to the local field params
            if location:
                self.longitude = location.longitude
                self.latitude = location.latitude

        # If we can't geocode because we've exeeded data then don't do anything.
        # Users can click on the map if they like, which doesn't require any
        # geocoding.
        except GeocoderServiceError:
            LOG.info('GEOCODEER ERROR - Maybe we\'ve exceeded the quota')

    def close_account(self):
        errors = []
        user = self.user

        # cc3_profile = user.get_profile()

        # 1. mark auth_user record as inactive
        LOG.info(u"Close account: Setting user {0} inactive".format(
            user.username))
        user.is_active = False
        user.save()

        # 1a. Disable any ads, so they're no longer shown in the marketplace
        for ad in self.ad_set.all():
            LOG.info(u"Close account: Disabling ad '{0}' for user {1}".format(
                ad, user.username))
            ad.disable_ad()

        # 1b. Cancel any card applications
        for fulfillment in self.fulfillment_set.all():
            LOG.info(u"Close account: Cancelling card fulfillment '{0}' "
                     u"for user {1}".format(
                        fulfillment, user.username))
            fulfillment.cancel()

        # 2. transfer any remaining positive balance back to the
        # Samen Doen - Positoos account
        # transferTypeId=52
        # Need to do this _before_ making the Cyclos user inactive
        balance_transfer_type_id = getattr(
            settings, 'CLOSE_ACCOUNT_BALANCE_TRANSFER_TYPE_ID', 52)
        balance_transfer_description = getattr(
            settings, 'CLOSE_ACCOUNT_BALANCE_TRANSFER_DESC',
            "Balance transfer on closing account")

        balance = self.current_balance

        if balance > 0:
            LOG.info(u"Close account: Transferring balance for user {0}, "
                     u"current balance {1}".format(
                        user.username, balance))

            LOG.info(u"Credit transfer, ID: {0}, {1}".format(
                balance_transfer_type_id, balance_transfer_description))
            try:
                backends.to_system_payment(
                    user.username, balance, balance_transfer_description,
                    transfer_type_id=balance_transfer_type_id)
            except TransactionException, e:
                error_msg = u'Unable to perform balance transfer. ' \
                            u'The transaction failed'.format(e)
                LOG.error(error_msg)
                errors.append(error_msg)
        else:
            LOG.info(u"Close account: No balance transfer needed for user {0}, "
                     u"current balance {1}".format(
                        user.username, balance))

        # 3. move cyclos account into "inactive accounts" cyclos group
        LOG.info(u"Close account: Moving user {0} to Inactive Members "
                 u"Cyclos group".format(user.username))
        inactive_group = None
        try:
            inactive_group = CyclosGroup.objects.get(
                name=settings.CYCLOS_INACTIVE_MEMBER_GROUP)
        except CyclosGroup.DoesNotExist:
            LOG.critical('Inactive members Cyclos group does not exist.')
        except AttributeError:
            LOG.critical("Django setting CYCLOS_INACTIVE_MEMBER_GROUP not"
                         " defined.")
        if inactive_group:
            try:
                backends.update_group(self.cyclos_account.cyclos_id,
                                      inactive_group.id,
                                      ugettext(u"User closed account"))

                self.cyclos_group = inactive_group
                self.web_payments_enabled = False
                self.save()
            except:
                msg = u'Unable to change Cyclos group'
                LOG.error(msg)
                errors.append(msg)
        else:
            msg = u'Unable to change Cyclos group'
            LOG.error(msg)
            errors.append(msg)

        # 4. mark any cards as inactive
        for card in user.card_set.all():
            LOG.info(u"Close account: Disabling card {1} for user {0}".format(
                user.username, card.number))
            card.block_card()

        # if there were any errors, mail the admins so they can put it right
        # (the user doesn't need to know)
        if errors:
            message = u"The following error(s) occurred when user {0} " \
                      u"closed their account:\n- {1}".format(
                          user.username, '\n- '.join(errors))
            mail_admins(u'Errors closing account',
                        message, fail_silently=True)

        # send signal, so that StadlanderProfile can update external system
        # 3280
        account_closed_signal.send(sender=CC3Profile, instance=self)

    def estimated_charges_by_period(self, period):
        result = Decimal(0.00)
        today_next_month = date.today()
        today_next_month += relativedelta(months=+1)
        first_of_next_month = date(
            today_next_month.year, today_next_month.month, 1)
        assigned_products = self.assigned_products.filter(
            product__billing_frequency=period)

        if not assigned_products:
            return False

        for assigned_product in assigned_products:
            pricing = assigned_product.get_prices_for_date(
                first_of_next_month)

            if pricing:
                result += pricing['total_price_ex_tax']

        return result

    @property
    def estimated_monthly_charges(self):
        return self.estimated_charges_by_period(BILLING_PERIOD_MONTHLY)

    @property
    def estimated_yearly_charges(self):
        return self.estimated_charges_by_period(BILLING_PERIOD_YEARLY)


def is_cc3_member(user):
    """ Is the user a `real` member and not a `system` user """
    return not user.is_superuser and user.id is not None and \
        user.id not in SYSTEM_USER_IDS


class CyclosStatus(models.Model):
    """
    Record what state the cyclos account has got to...
     - temporary (registration started)
     - complete
     - cyclos user linked / created

    """
    code = models.CharField(max_length=5, blank=True, default='')
    description = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        app_label = 'cyclos'
        verbose_name_plural = _(u'cyclos statuses')

    def __unicode__(self):
        return u'{0}'.format(self.description)


class CyclosAccount(models.Model):
    """A 'member' account in Cyclos"""
    cyclos_id = IntegerField(
        _(u'Cyclos account ID'), primary_key=True, name='cyclos_id')
    cc3_profile = models.OneToOneField(
        CC3Profile, verbose_name=_(u'cc3 profile'),
        related_name='cyclos_account')
    cyclos_group = models.SmallIntegerField(
        _(u'Cyclos Group ID'), null=True, blank=True,
        help_text=_('Cyclos backend group ID.'))

    # Custom manager
    objects = CyclosAccountManager()

    class Meta:
        app_label = 'cyclos'
        ordering = ('cc3_profile__user__username',)

    def __unicode__(self):
        return u'{0} - Cyclos ID: {1}'.format(
            self.cc3_profile.user.username, self.cyclos_id)

    def save(self, force_insert=False, force_update=False, using=None,
             update_field=None):
        """
        Overrides base class ``save()`` method to create the Cyclos profile
        when saving.

        Having a ``cyclos_group`` defined on model creation, that Cyclos group
        will be assigned to the profile. Otherwise, the group defined as the
        'initial group' will be assigned.
        """
        extra_fields = {}

        fields = getattr(settings, 'CC3_PROFILE_FIELDS_TO_CYCLOS', {})
        if fields:
            for key, value in fields.iteritems():
                extra_fields[key] = getattr(self.cc3_profile, value, None)

        if not self.cyclos_id or force_insert and self.cc3_profile.community:
            # Define the initial group for the profile. Can be the settings
            # configured or the one defined in ``self.cyclos_group``.
            if not self.cyclos_group:
                initial_groups = self.cc3_profile.community.get_initial_groups(
                    self.cc3_profile.groupset)
                if len(initial_groups) > 1:
                    LOG.warning(
                        u"Warning: Multiple initial CyclosGroups for "
                        u"community {0} defined, picking the first one".format(
                            self.cc3_profile.community))

                if initial_groups:
                    initial_group_id = initial_groups[0].id
                else:
                    error_str = \
                        u"Error: no initial CyclosGroup for " \
                        u"community {0} defined".format(
                            self.cc3_profile.community)
                    LOG.error(error_str)
                    raise IntegrityError(error_str)
            else:
                initial_group_id = self.cyclos_group

            # Check if the account, for any reason, was already existent in
            # Cyclos backend.
            existent = None
            username_to_check = self.cc3_profile.user.username
            existing_users = backends.search(username=username_to_check)
            for existing_user in existing_users:
                if existing_user[3] == username_to_check:
                    existent = existing_user

            if not existent:

                # SDW: NB - cyclos initial group set in cyclos, not saved to
                # django. Also - group set by another method in SamenDoen -
                # via the 'IndividualProfile' save method.

                # Create the new account.
                new_account = backends.new(
                    self.cc3_profile.user.username,
                    u'{0} {1}'.format(self.cc3_profile.first_name,
                                      self.cc3_profile.last_name),
                    self.cc3_profile.user.email,
                    self.cc3_profile.business_name,
                    initial_group_id,
                    community_code=self.cc3_profile.community.code,
                    extra_fields=extra_fields
                )

                self.cyclos_id = new_account.id
            else:
                # Assign the previously created account.
                self.cyclos_id = existent[0]
        else:
            # An update
            backends.update(
                self.cc3_profile.cyclos_account.cyclos_id,
                u'{0} {1}'.format(self.cc3_profile.first_name,
                                  self.cc3_profile.last_name),
                self.cc3_profile.user.email,
                self.cc3_profile.business_name,
                self.cc3_profile.community.code,
                extra_fields=extra_fields
            )

        return super(CyclosAccount, self).save(
            force_insert=force_insert, force_update=force_update, using=using)

    @property
    def user(self):
        """User instance linked to this Cyclos account"""
        return self.cc3_profile.user


@receiver(post_save, sender=CC3Profile,
          dispatch_uid='cc3_qoin_profile_save')
def link_account(sender, instance, created, **kwargs):
    """ Create cyclos user if/when the profile has been completed.
    (ie the user is serious). Also send an email once the profile has been
    completed, and mark the profile accordingly"""

    # Only create the cyclos account once a first and last name have been
    # entered into the profile
    if not created:
        if instance.first_name and instance.last_name:
            try:
                # TODO: figure out what has changed, only sync name and email
                instance.cyclos_account.save()
            except CyclosAccount.DoesNotExist:
                # 'legacy' accounts
                LOG.debug(
                    'Existing account without a linked Cyclos account, '
                    'creating new account in Cyclos')
                CyclosAccount.objects.create(cc3_profile=instance)

        if instance.has_completed_profile() and \
                not instance.has_notified_profilecomplete:
            LOG.info('Sending notifications to community admins about user '
                     'completing profile')

            profile_edit_url = "http://{0}{1}".format(
                Site.objects.get_current().domain,
                reverse(
                    'communityadmin_ns:editmember',
                    kwargs={'username': instance.user.username}))
            mail_community_admins(
                instance, MAIL_TYPE_PROFILE_COMPLETED,
                translation.get_language(),
                extra_context={
                    'profile_edit_url': profile_edit_url
                }
            )

            instance.has_notified_profilecomplete = True
            instance.save()


@receiver(post_save, sender=CC3Profile,
          dispatch_uid='cc3_qoin_new_profile_notify')
def notify_community_admins(sender, instance, created, **kwargs):
    """
    Upon creation of a new user check if the admins for this community wants a
    notification.
    """
    LOG.info(u'In notify receiver, instance {0} created: {1}'.format(
        instance, created))
    if created and instance.community and \
            instance.community.newreg_notify_cadmin:
        LOG.info('Sending notifications to community admins about new user')

        mail_community_admins(
            instance, MAIL_TYPE_NEW_REGISTRATION, translation.get_language())


def ignore_configured_categories(category_id_list):
    filtered_list = []
    for cat in Category.objects.filter(id__in=category_id_list).all():
        if not cat.ignore_for_matching:
            filtered_list.append(cat.id)
    return filtered_list


@receiver(pre_save, sender=CC3Profile,
          dispatch_uid='profile_cache_categories')
def cache_categories(sender, instance, **kwargs):
    if instance.pk:
        instance._old_categories = set(
            list(instance.categories.values_list('pk', flat=True)))
        instance._old_want_categories = set(
            list(instance.want_categories.values_list('pk', flat=True)))
    else:
        instance._old_categories = set(list())
        instance._old_want_categories = set(list())


@receiver(m2m_changed, sender=CC3Profile.categories.through,
          dispatch_uid='profile_categories_changed')
def categories_changed(sender, instance, action, **kwargs):
    pk_set = kwargs['pk_set']
    if action == "post_add":
        try:
            old_categories = instance._old_categories
        except AttributeError:
            old_categories = set(list())
        added_categories = ignore_configured_categories(
            list(pk_set.difference(old_categories)))
        deleted_categories = ignore_configured_categories(
            list(old_categories.difference(pk_set)))
        for cat_id in added_categories:
            TrackedProfileCategory.objects.create(
                profile=instance, category_id=cat_id,
                category_type=TrackedProfileCategory.TYPE_OFFER)
        for cat_id in deleted_categories:
            TrackedProfileCategory.objects.filter(
                profile=instance, category_id=cat_id,
                category_type=TrackedProfileCategory.TYPE_OFFER).delete()
        if added_categories:
            instance.handle_updated_categories(added_categories)


@receiver(m2m_changed, sender=CC3Profile.want_categories.through,
          dispatch_uid='profile_want_categories_changed')
def want_categories_changed(sender, instance, action, **kwargs):
    pk_set = kwargs['pk_set']
    if action == "post_add":
        try:
            old_want_categories = instance._old_want_categories
        except AttributeError:
            old_want_categories = set(list())
        added_want_categories = ignore_configured_categories(
            list(pk_set.difference(old_want_categories)))
        deleted_want_categories = ignore_configured_categories(
            list(old_want_categories.difference(pk_set)))
        for cat_id in added_want_categories:
            TrackedProfileCategory.objects.create(
                profile=instance, category_id=cat_id,
                category_type=TrackedProfileCategory.TYPE_WANT)
        for cat_id in deleted_want_categories:
            TrackedProfileCategory.objects.filter(
                profile=instance, category_id=cat_id,
                category_type=TrackedProfileCategory.TYPE_WANT).delete()

        if added_want_categories:
            instance.handle_updated_want_categories(added_want_categories)


@receiver(post_save, sender=AuthUser, dispatch_uid='django_user_cyclos_update')
def django_user_cyclos_account_update(sender, instance, created, **kwargs):
    """
    On saving the Django ``User`` models, update the Cyclos account if needed.

    Updating ``email`` field must be synced in Cyclos. To do this, we first
    check if there is any ``CyclosAccount`` related to this user. If so, and
    the ``User`` model is being updated, we trigger a ``CyclosAccount.save()``,
    to ensure the changes are updated also in Cyclos.
    """
    if not created:
        try:
            cc3_profile = CC3Profile.objects.get(
                user__username=instance.username)
            cyclos_account = CyclosAccount.objects.get(cc3_profile=cc3_profile)
            cyclos_account.save()
        except ObjectDoesNotExist:
            # User is not present in Cyclos. Syncing not needed.
            pass


def update_first_login_state(sender, request, user, **kwargs):
    """
    A signal receiver which updates the last_login date for
    the user logging in.
    """
    try:
        cc3_profile = user.get_profile()

        if cc3_profile.first_login is None:
            cc3_profile.first_login = True
            cc3_profile.save()
        else:
            if cc3_profile.first_login:
                cc3_profile.first_login = False
                cc3_profile.save()

        request.session['first_login'] = cc3_profile.first_login

    except ObjectDoesNotExist:
        pass


# Signal handler that creates an instance of UserStatusChangeHistory when a
# user account is activated/deactivated
@receiver(post_save, sender=User, dispatch_uid='user_status_change_notify')
def log_user_status_change(instance, created, raw, **kwargs):
    # If no request object, that means the user object is NOT being changed
    # from a view
    # Using None change author
    change_author = None

    # Get the current user from the request object passed via the dedicated
    # middleware
    if hasattr(log_user_status_change, 'change_author'):
        change_author = log_user_status_change.change_author

    # If the user is anonymous (e.g., confirming account registration)
    # skip the rest of the function
    if change_author:
        is_authenticated = getattr(change_author, 'is_authenticated')
        if callable(is_authenticated):
            if not is_authenticated():
                return

    try:
        # Log the status change only if the user already exists.
        # Upon user creation, this information is already captured by the user
        # registration_date field
        if not created:
            # Log if the is_active flag has changed or not
            if instance.is_active_has_changed() or \
                    (hasattr(instance, 'is_active_changed') and
                     instance.is_active_changed):
                UserStatusChangeHistory.objects.create(
                    user=instance, change_author=change_author,
                    timestamp=datetime_now(), activate=instance.is_active)
    except IntegrityError as e:
        LOG.error(e)


# Signal handler that calls log_user_status_change() when an AuthUser
# instance's is_active field is changed
@receiver(post_save, sender=AuthUser,
          dispatch_uid='auth_user_status_change_relay_notify')
def relay_auth_user_post_save_signal(instance, created, raw, **kwargs):
    if instance is not None and hasattr(instance, 'id') and \
            instance.id is not None:
        try:
            # Get the User instance corresponding to the AuthUser that was saved
            user = User.objects.get(id=instance.id)
        except User.DoesNotExist:
            LOG.error('User with id {} does not exist, cannot set '
                      'is_active_changed flag on User instance.'.format(id))
            return

        # If the AuthUser instance's is_active flag changed,
        # set the corresponding flag for the User instance
        # Only relay to log_user_status_change() in that case
        if hasattr(instance, 'is_active_changed'):
            if instance.is_active_changed:
                user.is_active_changed = True
                log_user_status_change(
                    instance=user, created=created, raw=raw, **kwargs)


# Signal handler that gets triggered by AuthUser's pre_save signal to detect
# if the is_active field has changed. Uses the 'is_active_changed' instance
# attribute to notify the post_save signal handler of such change
@receiver(pre_save, sender=AuthUser,
          dispatch_uid='auth_user_status_change_detect_notify')
def flag_user_status_change(sender, instance, raw, **kwargs):
    if instance is not None and hasattr(instance, 'id') and \
            instance.id is not None:
        try:
            # The user corresponding to the User instance to be saved
            user = User.objects.get(id=instance.id)
            # Compare the is_active flags of the two instances
            if user.is_active != instance.is_active:
                # If they don't match use an instance attribute to pass
                # the "changed" flag to the post_save method
                instance.is_active_changed = True
        except User.DoesNotExist:
            LOG.error('User with id {} does not exist, '
                      'cannot set is_active_changed flag '
                      'on User instance.'.format(instance.id))

user_logged_in.connect(update_first_login_state)


class FulfillmentProfileProxyModel(CC3Profile):
    class Meta:
        proxy = True
        app_label = 'accounts'
        verbose_name = _('CC3Profile (Fulfillment)')
        verbose_name_plural = _('Profile (Fulfillment)')
        # app label causes migrations to be created in the auth app
        managed = False
