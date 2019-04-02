from datetime import datetime
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import get_language, ugettext_lazy as _

from adminsortable.fields import SortableForeignKey
from adminsortable.models import Sortable
from easy_thumbnails.fields import ThumbnailerImageField
from taggit.managers import TaggableManager
from tinymce.models import HTMLField

from cc3.core.models import Transaction, LocationMixin
from cc3.cyclos.models import CC3Profile, CommunityAdmin
from cc3.mail.utils import send_mail_to
from cc3.mail.models import (
    MAIL_TYPE_CAMPAIGN_SIGNUP_CONFIRM,
    MAIL_TYPE_CAMPAIGN_SIGNUP_NOTIFY, MAIL_TYPE_CAMPAIGN_UPDATED,
    MAIL_TYPE_CAMPAIGN_CANCELLED, MAIL_TYPE_CAMPAIGN_UNSUBSCRIBED,
    MAIL_TYPE_CAMPAIGN_CREATED,
)
from cc3.rewards.utils import pay_reward_with_cause_donation

from .utils import get_ad_image_filename, get_campaign_image_filename
from .common import (AD_STATUS_CHOICES, AD_STATUS_ACTIVE,
                     AD_STATUS_ONHOLD, AD_STATUS_DISABLED)

from django.db.models import Q

LOG = logging.getLogger('cc3.marketplace')


class AdType(models.Model):
    code = models.CharField(max_length=4)
    title = models.CharField(
        max_length=50, choices=[('O', _(u'Offer')), ('W', _(u'Want'))],
        help_text=(_(u'Offer or Want in MVP - to be translated?')))
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return self.get_title_display()


class AbstractImage(models.Model):
    class Meta:
        abstract = True
    date_created = models.DateTimeField("Date created", auto_now_add=True)
    user_created = models.ForeignKey(
        'cyclos.User', null=True, blank=True, verbose_name=_(u"Created by"))
    caption = models.CharField(
        max_length=200, null=True, blank=True,
        help_text=_(u"A caption to be displayed or used as alt text"))
    height = models.IntegerField(blank=True, null=True, editable=False)
    width = models.IntegerField(blank=True, null=True, editable=False)
    url = models.URLField(blank=True, null=True, editable=False)


class AdImage(AbstractImage, models.Model):
    """
    Model containing info about images used for offers / wants.
    'easy_thumbnails' module used to manage image thumbnails.
    """
    is_active = models.BooleanField(
        default=True, editable=False,
        help_text=_(u"Not currently in use, but could hide images when "
                    u"unticked if implemented"))
    order = models.IntegerField(
        default=0, editable=False, help_text=_(u"Not currently in use"))
    image = ThumbnailerImageField(
        upload_to=get_ad_image_filename, blank=True, height_field="height",
        width_field="width")
    ad = models.ForeignKey('Ad', null=True, blank=True)

    def __unicode__(self):
        return u'{0}'.format(self.caption)

    class Meta:
        ordering = ['order']

    def get_image(self):
        """
        In order to allow template to fail gracefully, move exception handling
        up to model
        :return: image (thumbnailable image) or None
        """
        try:
            if self.image.file:
                return self.image
        except ValueError:
            return None
        except IOError:
            return None


class PreAdImage(AbstractImage):
    """
    Model containing 'pre-Ad' images, eg: images that are uploaded
    while a user is still creating a new Ad.

    These images are turned into AdImages if the Ad is saved, otherwise
    they are deleted when the user starts creating a new Ad.
    """
    image = ThumbnailerImageField(
        upload_to='ad_images_p', blank=True, height_field="height",
        width_field="width")


class AdPricingOptionTranslation(models.Model):
    title = models.CharField(max_length=50, help_text=(_(u'Pricing option')))
    language = models.CharField(max_length=5, choices=settings.LANGUAGES)
    ad_pricing_option = models.ForeignKey('AdPricingOption')

    class Meta:
        unique_together = ('language', 'ad_pricing_option')
        ordering = ['ad_pricing_option', 'language']

    def __unicode__(self):
        return self.title


class AdPricingOption(models.Model):
    """
    Model detailing the specifics about a pricing option other than 'fixed
    price'.
    """
    title = models.CharField(max_length=50, help_text=(_(u'Pricing option')))

    def __unicode__(self):
        return self.get_title()

    def _get_translation(self):
        current_language = get_language()
        try:
            translation = self.adpricingoptiontranslation_set.get(
                language=current_language)
            return translation
        except AdPricingOptionTranslation.DoesNotExist:
            pass  # will try something else

        # try for languages like en-us
        if current_language.find('-') >= 0:
            language = current_language.split('-')[0]
            try:
                translation = self.adpricingoptiontranslation_set.get(
                    language=language)
                return translation
            except AdPricingOptionTranslation.DoesNotExist:
                return None

        return None

    def get_title(self):
        translation = self._get_translation()
        return translation.title if translation else self.title


class Ad(models.Model):
    title = models.CharField(
        _(u'Title'), max_length=255, help_text=_(u'Title of the offer/want'))
    adtype = models.ForeignKey(
        AdType, default=1, verbose_name=_(u'Offer or want'))
    description = HTMLField(verbose_name=_(u'Description'))
    price = models.DecimalField(
        _(u'Price'), max_digits=10, decimal_places=2, null=True, blank=True)
    price_option = models.ForeignKey(
        AdPricingOption, null=True, blank=True,
        verbose_name=_(u'Other pricing option'))
    barter_euros = models.DecimalField(
        _(u'Barter euros'), max_digits=10, decimal_places=2, null=True,
        blank=True)
    category = models.ManyToManyField(
        'core.Category', verbose_name=_(u'Categories'))
    keywords = TaggableManager(_(u'Keywords'), blank=True)
    views = models.IntegerField(_(u'Views'), default=0)
    created_by = models.ForeignKey('cyclos.CC3Profile')
    date_created = models.DateTimeField("Date created", auto_now_add=True)
    status = models.CharField(
        max_length=50, choices=AD_STATUS_CHOICES, default=AD_STATUS_ACTIVE,
        help_text=_('Only community administrators may change "on hold" ads'))

    def __unicode__(self):
        return u'{0}'.format(self.title)

    def get_absolute_url(self):
        return reverse(
            'marketplace-detail', kwargs={'pk': self.pk})

    def get_price(self):
        """
        Returns a unicode string with the price for this Ad, or the name of
        the pricing option if no price is known.
        """
        if self.price is not None:
            return unicode(self.price)
        if self.price_option:
            return unicode(self.price_option)

        return unicode('0.00')

    def disable_ad(self):
        self.status = AD_STATUS_DISABLED
        self.save()

    @property
    def created_by_email(self):
        return u'{0}'.format(self.created_by.user.email)

    @property
    def business_name(self):
        return u'{0}'.format(self.created_by.business_name)

    @property
    def business_slug(self):
        return u'{0}'.format(self.created_by.slug)

    @property
    def business_picture(self):
        if self.created_by.get_picture():
            return u'{0}'.format(self.created_by.picture)
        else:
            return u''

    def can_edit(self, user):
        """ can the given user edit this Ad? """
        if user.is_superuser:
            return True

        try:
            # USE PK here, as profile types can vary
            # (ie UserProfile - inherits CC3Profile)
            if user.cc3_profile.pk == self.created_by.pk:
                return True
        except CC3Profile.DoesNotExist:
            pass

        if user.get_admin_community() == self.created_by.community:
            return True

        return False

    def can_view(self, user):
        """ can the given user view this Ad? """
        if self.status == AD_STATUS_ACTIVE:
            return True

        if user.is_authenticated() is False:
            return False

        if user.is_superuser:
            return True

        try:
            if user.cc3_profile == self.created_by:
                return True
        except CC3Profile.DoesNotExist:
            pass  # carry on

        try:
            if user.get_admin_community() == self.created_by.community:
                return True
        except CommunityAdmin.DoesNotExist:
            pass

        return False


# Function that checks if a profile should be visible based on
# the various models that impact user visibility
def check_profile_visibility(profile):
    joined_campaigns = True
    has_ads = True

    # If the profile is in one of the consumer groups
    if profile.cyclos_group and profile.cyclos_group.name \
            in getattr(settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', []):
        # Then get the active ads for the profile
        profile_ads = Ad.objects.filter(
            created_by=profile).filter(status=AD_STATUS_ACTIVE)

        # If there there are any make sure the profile is visible, or
        # not if there aren't
        if profile_ads.count() > 0:
            if not profile.is_visible:
                profile.is_visible = True
                profile.save()
                return
        else:
            has_ads = False

        # Get the campaigns that the user has joined
        # That are not cancelled AND that are not finished
        campaigns = Campaign.objects.filter(
                        ~Q(status=CAMPAIGN_STATUS_CANCELLED),
                        participants__profile=profile,
                        start_date__gte=datetime.now().date()).exclude(
                                                        start_date=datetime.now().date(),
                                                        end_time__lte=datetime.now().time())
        # If there are joined campaigns
        if campaigns.count() > 0:
            # Set the profile to visible if not already set
            if not profile.is_visible:
                profile.is_visible = True
                profile.save()
                return
        else:
            joined_campaigns = False

        # If the user has not joined any campaigns, does not own any ads and
        # has a profile set to visible, set it to invisible
        if not joined_campaigns and not has_ads and profile.is_visible:
            profile.is_visible = False
            profile.save()


@receiver(post_save, sender=Ad)
def handle_ad_post_save(sender, instance, **kwargs):
    check_profile_visibility(instance.created_by)


def notify_ad_on_hold(sender, instance, created, **kwargs):
    """
    Whenever an Ad is created or updated and placed "On Hold",
    send an email to notify the community admins
    """
    from cc3.mail.models import MailMessage, MAIL_TYPE_AD_ONHOLD

    if not instance.status == AD_STATUS_ONHOLD:
        return
    try:
        msg = MailMessage.objects.get_msg(MAIL_TYPE_AD_ONHOLD,
                                          lang=get_language())
    except MailMessage.DoesNotExist:
        LOG.warning('Not sending Ad on hold notification, the email template'
                    ' doesn\'t exist.')
        return

    site = Site.objects.get_current()
    ad_url = "http://{0}{1}".format(
        site.domain, reverse('communityadmin_ns:edit_ad',
                             kwargs={'pk': instance.pk}))
    context = {
        'ad_url': ad_url,
    }
    for comm_admin in instance.created_by.community.get_administrators():
        if comm_admin.user.email:
            msg.send(comm_admin.user.email, context)

# Only connect this handler if needed
if getattr(settings, 'MARKETPLACE_ADS_NEED_APPROVAL', False):
    post_save.connect(notify_ad_on_hold, sender=Ad,
                      dispatch_uid='cc3_qoin_ad_onhold_notify')


class AdPaymentTransaction(Transaction):
    """
    Subclasses core model ``core.Transaction``.

    Stores the details for each successful transaction executed in the
    marketplace.
    """
    ad = models.ForeignKey(
        Ad, blank=True, null=True,
        help_text=_('Ad related to payment or None if direct payment'))
    title = models.CharField(max_length=255)
    split_payment_total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text=_('Total amount, in case of BYB/split-currency payments'))


@receiver(post_save, sender=AdPaymentTransaction,
          dispatch_uid='cc3_qoin_new_transaction_notify')
def notify_community_admins(sender, instance, created, **kwargs):
    """
    Upon completion of a payment check if the community admins want a
    notification.
    """
    from cc3.mail.models import MailMessage, MAIL_TYPE_NEW_PAYMENT

    LOG.info('In notify receiver, instance {0} created: {1}'.format(
             unicode(instance), unicode(created)))
    sender = instance.sender
    _receiver = instance.receiver
    sender_community = sender.get_community()
    receiver_community = _receiver.get_community()

    try:
        sender_profile = sender.get_profile()
        receiver_profile = _receiver.get_profile()
    except ObjectDoesNotExist:
        LOG.error(u'Not sending mail to community admin. Profile for sender '
                  u'{0} or receiver {1} does not exist'.format(
                      sender, _receiver))
        return

    context = {
        'payment': instance,
        'sender': sender_profile,
        'receiver': receiver_profile
    }

    if created and sender_community and \
            sender_community.transcomplete_notify_cadmin:
        LOG.info('Sending notifications to community admins about new '
                 'transaction')
        try:
            msg = MailMessage.objects.get_msg(MAIL_TYPE_NEW_PAYMENT,
                                              lang=get_language())
        except Exception as e:
            LOG.warning('Not sending new user notification, the email template'
                        ' doesn\'t exist.')
            LOG.warning(e)
            return
        for comm_admin in sender_community.get_administrators():
            if comm_admin.user.email:
                msg.send(comm_admin.user.email, context)

        if sender_community != receiver_community and \
                receiver_community.transcomplete_notify_cadmin:
            LOG.info('Sending notifications to community admins about new '
                     'transaction')
            try:
                msg = MailMessage.objects.get_msg(MAIL_TYPE_NEW_PAYMENT,
                                                  lang=get_language())
            except MailMessage.DoesNotExist:
                LOG.warning(
                    'Not sending new user notification, the email template'
                    ' doesn\'t exist.')
                return
            for comm_admin in receiver_community.get_administrators():
                if comm_admin.user.email:
                    msg.send(comm_admin.user.email, context)


##############################
# Campaigns (see ticket #2594)
##############################

class CampaignCategoryManager(models.Manager):

    def for_campaigns(self):
        """
        Return all CampaignCategories that visible campaigns
        """
        return self.active().exclude(campaign__isnull=True).distinct()

    def active(self):
        return self.model.objects.filter(active=True)


class CampaignCategory(Sortable):
    parent = SortableForeignKey(
        'self', null=True, blank=True, related_name='children')
    title = models.CharField(max_length=100, help_text=(_(u'Category title')))
    description = models.CharField(
        max_length=255, help_text=(_(u'Category description')))
    active = models.BooleanField(
        default=True, help_text=_(u'Marks this Category as active'))

    objects = CampaignCategoryManager()

    class Meta(Sortable.Meta):
        verbose_name_plural = _(u'categories')
        ordering = ('order', 'title')

    def __unicode__(self):
        return u'{0}'.format(self.get_title())

    def _get_translation(self):
        current_language = get_language()
        try:
            translation = self.translations.get(
                language=current_language)
            return translation
        except CampaignCategoryTranslation.DoesNotExist:
            pass  # will try something else

        # try for languages like en-us
        if current_language.find('-') >= 0:
            language = current_language.split('-')[0]
            try:
                translation = self.translations.get(
                    language=language)
                return translation
            except CampaignCategoryTranslation.DoesNotExist:
                return None

        return None

    def get_title(self):
        translation = self._get_translation()
        return translation.title if translation else self.title

    def get_description(self):
        translation = self._get_translation()
        return translation.description if translation else self.description


class CampaignCategoryTranslation(models.Model):
    title = models.CharField(max_length=50, help_text=(_(u'Category title')))
    description = models.CharField(max_length=255)
    language = models.CharField(max_length=5, choices=settings.LANGUAGES)
    category = models.ForeignKey(
        'marketplace.CampaignCategory', related_name="translations",
        null=True, blank=True)

    class Meta:
        unique_together = ("language", "category")

    def __unicode__(self):
        return u"{0}".format(self.title)


CAMPAIGN_STATUS_VISIBLE = 'V'
CAMPAIGN_STATUS_HIDDEN = 'H'
CAMPAIGN_STATUS_CANCELLED = 'C'
CAMPAIGN_STATUS_CHOICES = (
    (CAMPAIGN_STATUS_VISIBLE, _(u"Published")),
    (CAMPAIGN_STATUS_HIDDEN, _(u"Not published")),
    (CAMPAIGN_STATUS_CANCELLED, _(u"Cancelled")),
)

class Campaign(LocationMixin, models.Model):
    title = models.CharField(
        _(u'Title'), max_length=60, help_text=_(u'Title of the activity'))
    description = HTMLField(verbose_name=_(u'Description of the activity'))
    image = ThumbnailerImageField(
        _('Image'), upload_to=get_campaign_image_filename, blank=True,
        height_field='image_height', width_field='image_width',
        default='')
    image_height = models.IntegerField(
        _('Image height'), blank=True, null=True, editable=False)
    image_width = models.IntegerField(
        _('Image width'), blank=True, null=True, editable=False)
    criteria = models.CharField(
        _(u'Criteria for participants'), max_length=100, blank=True)
    communities = models.ManyToManyField(
        'cyclos.CC3Community', verbose_name=_(u'Participating communities'))
    start_date = models.DateField(_(u'Date of activity'))
    start_time = models.TimeField(_(u'Start time'))
    end_time = models.TimeField(_(u'End time'))
    categories = models.ManyToManyField(
        CampaignCategory, verbose_name=_(u'Categories'))
    max_participants = models.IntegerField(
        _(u'Number of participants needed'))
    reward_per_participant = models.DecimalField(
        _(u'Reward per participant'), max_digits=10, decimal_places=2)
    contact_name = models.CharField(
        _(u'Contact name'), max_length=100)
    contact_telephone = models.CharField(
        _(u'Contact telephone number'), max_length=100, blank=True)
    contact_email = models.EmailField(
        _(u'Contact email'), max_length=100)
    created_by = models.ForeignKey('cyclos.CC3Profile')
    date_created = models.DateTimeField("Date created", auto_now_add=True)
    status = models.CharField(
        max_length=1, choices=CAMPAIGN_STATUS_CHOICES,
        default=CAMPAIGN_STATUS_VISIBLE)
    why_cancelled = models.TextField(
        _(u'Reason for cancellation (if cancelled)'),
        blank=True)

    def __unicode__(self):
        return u'{0} | {1}'.format(self.title, self.start_date)

    @property
    def has_finished(self):
        ends_at = datetime(
            self.start_date.year, self.start_date.month, self.start_date.day,
            self.end_time.hour,  self.end_time.minute,  self.end_time.second)
        return datetime.now() >= ends_at

    @property
    def in_progress(self):
        now = datetime.now()
        starts_at = datetime(
            self.start_date.year, self.start_date.month, self.start_date.day,
            self.start_time.hour, self.start_time.minute,
            self.start_time.second)
        ends_at = datetime(
            self.start_date.year, self.start_date.month, self.start_date.day,
            self.end_time.hour, self.end_time.minute, self.end_time.second)
        return starts_at <= now < ends_at

    @property
    def is_live(self):
        """i.e. has not yet finished or been cancelled"""
        if self.status == CAMPAIGN_STATUS_CANCELLED:
            return False
        if self.has_finished:
            return False
        return True

    @property
    def is_editable(self):
        """i.e. may be edited (by appropriate user)

        Currently the same as 'is_live' but retained in case
        they need to diverge
        """
        return self.is_live

    @property
    def is_cancelled(self):
        return self.status == CAMPAIGN_STATUS_CANCELLED

    @property
    def is_visible(self):
        # TODO: check whether this should include cancelled or not
        return self.status != CAMPAIGN_STATUS_HIDDEN

    @property
    def num_participants_required(self):
        return self.max_participants - self.participants.count()

    @property
    def max_reward_payable(self):
        return self.max_participants * self.reward_per_participant

    @property
    def reward_currently_payable(self):
        return self.participants.count() * self.reward_per_participant

    @property
    def pretty_status(self):
        if self.has_finished:
            return _(u'Finished')
        elif self.in_progress:
            return _(u'In progress')
        return self.get_status_display()

    @property
    def owner_email(self):
        """Email address that receives notifications about this campaign

        TODO...TBC: contact_email if set, otherwise the creator
        """
        if self.contact_email:
            return self.contact_email
        return self.created_by.user.email

    def get_absolute_url(self):
        return reverse(
            'campaign-detail', kwargs={'pk': self.pk})

    def has_participant(self, cc3profile):
        return self.participants.filter(profile=cc3profile).count() > 0

    def add_participant(self, cc3profile):
        CampaignParticipant.objects.create(campaign=self,
                                           profile=cc3profile)

    def remove_participant(self, cc3profile):
        self.participants.filter(profile=cc3profile).delete()

    def _common_mail_context(self):
        return {
            'campaign': self,
            'cc3_system_name': getattr(
                settings, "CC3_SYSTEM_NAME", "TradeQoin")
        }

    def notify_participants(self, mail_type):
        sent = 0
        language = get_language()
        context = self._common_mail_context()
        for p in self.participants.all():
            context['profile'] = p.profile
            sent += send_mail_to(
                recipients=(p.profile,),
                mail_type=mail_type,
                language=language,
                context=context)

    def notify_participants_of_update(self):
        return self.notify_participants(
            mail_type=MAIL_TYPE_CAMPAIGN_UPDATED)

    def notify_participants_of_cancellation(self):
        return self.notify_participants(
            mail_type=MAIL_TYPE_CAMPAIGN_CANCELLED)

    def send_signup_notifications(self, profile):
        # send email confirmation to new participant, and
        # notification to the contact email
        language = get_language()
        context = self._common_mail_context()
        # provide both member and profile for backward compatibility
        context['member'] = profile
        context['profile'] = profile
        send_mail_to(
            recipients=(profile,),
            mail_type=MAIL_TYPE_CAMPAIGN_SIGNUP_CONFIRM,
            language=language,
            context=context)
        send_mail_to(
            recipients=(),
            recipient_addresses=(self.owner_email,),
            mail_type=MAIL_TYPE_CAMPAIGN_SIGNUP_NOTIFY,
            language=language,
            context=context)

    def send_creation_notifications(self):
        sent = 0

        if self.status != CAMPAIGN_STATUS_VISIBLE:
            return sent

        target_groups = getattr(
            settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', ())
        language = get_language()
        context = self._common_mail_context()
        for community in self.communities.filter(
                newcampaign_notify_members=True):
            for member in community.cc3profile_set.filter(
                    email_new_campaigns=True,
                    cyclos_group__name__in=target_groups):
                # provide both member and profile for backward compatibility
                context['member'] = member
                context['profile'] = member
                sent += send_mail_to(
                            recipients=(member,),
                            mail_type=MAIL_TYPE_CAMPAIGN_CREATED,
                            language=language,
                            context=context)
        return sent

    def can_edit(self, user):
        """ can the given user edit this Campaign? """
        # so far only the owner can edit
        try:
            if user.cc3_profile.pk == self.created_by.pk:
                return True
        except CC3Profile.DoesNotExist:
            pass
        return False

    def is_same_community(self, user):
        try:
            profile = user.cc3_profile
            if profile.community in self.communities.all():
                return True
        except CC3Profile.DoesNotExist:
            pass
        return False

    def can_subscribe(self, user):
        """ can the given user subscribe to this Campaign? """
        try:
            profile = user.cc3_profile
            if profile.cyclos_group.name in getattr(
                    settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', ()) and \
                    profile.community in self.communities.all():
                return True
        except CC3Profile.DoesNotExist:
            pass
        return False

    def can_see(self, user):
        """ can the given user see this Campaign?

        Anyone can see campaigns as long as they're visible, and
        owner can always see
        """
        if self.created_by.user == user:
            return True
        return self.is_visible

    def rewards_all_paid(self):
        """True if all participants have been rewarded"""
        return (self.participants.filter(
            date_rewarded__isnull=True).count() == 0)

    def total_rewards_paid(self):
        """Total amount paid in rewards to participants"""
        total = Decimal(0.00)
        for p in self.participants.all():
            total += p.reward_amount
        return total

    def get_default_seconds(self):
        return (datetime.combine(self.start_date, self.end_time) -
                datetime.combine(self.start_date, self.start_time)
                ).total_seconds()

    def make_reward_payments(self):
        """Pay all participants who have not yet been paid

        Assumes valid start and end times have been set for each participant,
        (by RewardCampaignParticipantForm), and pays a reward based on
        these values.
        Ignores any who have already been paid, as indicated by a non-null
        date_rewarded
        """
        now = datetime.now()
        total = Decimal(0)
        for p in self.participants.filter(
                date_rewarded__isnull=True):
            reward_amount = p.get_reward_due()
            if reward_amount > 0:
                # make the actual payment,
                # and the associated donation to good cause
                reward_paid = pay_reward_with_cause_donation(
                    amount=reward_amount,
                    sender=self.created_by.user,
                    payee=p.profile.user,
                    description=self.__unicode__())
                if reward_paid:
                    total += reward_amount
            p.reward_amount = reward_amount
            p.date_rewarded = now
            p.save()
        return total

    def get_image(self):
        """
        In order to allow template to fail gracefully, move exception handling
        up to model
        :return: image (thumbnailable image) or None
        """
        try:
            if self.image.file:
                return self.image
        except ValueError:
            return None
        except IOError:
            return None


class CampaignParticipant(models.Model):
    campaign = models.ForeignKey(Campaign, related_name="participants")
    profile = models.ForeignKey('cyclos.CC3Profile', related_name="campaigns")
    date_joined = models.DateTimeField(auto_now_add=True)
    start_time = models.TimeField(
        _(u'Start time'), blank=True, null=True)
    end_time = models.TimeField(
        _(u'End time'), blank=True, null=True)
    date_rewarded = models.DateTimeField(blank=True, null=True)
    reward_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)

    def notify_participant_of_removal(self, reason=''):
        language = get_language()
        context = self.campaign._common_mail_context()
        context['reason'] = reason
        context['profile'] = self.profile
        return send_mail_to(recipients=(self.profile,),
                            mail_type=MAIL_TYPE_CAMPAIGN_UNSUBSCRIBED,
                            language=language,
                            context=context)

    def get_seconds_attended(self):
        if self.start_time and self.end_time:
            return (
                datetime.combine(self.campaign.start_date, self.end_time) -
                datetime.combine(self.campaign.start_date, self.start_time)
                ).total_seconds()
        return 0

    def get_reward_due(self):
        reward_due = Decimal(0)
        if self.reward_amount is None:
            reward_due = Decimal(
                self.get_seconds_attended() /
                self.campaign.get_default_seconds()
                ) * self.campaign.reward_per_participant
        if getattr(settings, 'CC3_CURRENCY_INTEGER_ONLY', False):
            return reward_due.quantize(Decimal('1'))
        else:
            return reward_due.quantize(Decimal('0.01'))

    @property
    def reward_is_pending(self):
        """True if campaign has finished, is not cancelled,
        and reward has not yet been paid"""
        if self.date_rewarded is None:
            if self.campaign.has_finished and not self.campaign.is_cancelled:
                return True
        return False


@receiver(post_delete, sender=CampaignParticipant)
@receiver(post_save, sender=CampaignParticipant)
def handle_campaign_participant_post_save_delete(sender, instance, **kwargs):
    check_profile_visibility(instance.profile)
