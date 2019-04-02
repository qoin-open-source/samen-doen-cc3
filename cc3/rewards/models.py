from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from cc3.cyclos.models import CC3Community


class BusinessCauseSettings(models.Model):
    """
    Represents the settings related to cause donations in a specific business.
    """
    system_name = getattr(settings, "CC3_SYSTEM_NAME", "Positoos")
    user = models.OneToOneField('cyclos.User', verbose_name=_('business'))
    transaction_percentage = models.DecimalField(
        _('transaction percentage'), max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text=_('Percentage of each transaction to be rewarded in '
                    '{0}').format(system_name))
    reward_percentage = models.BooleanField(
        _('reward by percentage'), default=False,
        help_text=_('Reward will be automatically calculated as a percentage '
                    'of the Euro transaction - percentage must be specified '
                    'above. If not selected a fixed amount of {0} is to '
                    'be entered.').format(system_name))

    class Meta:
        ordering = ('user__email',)
        verbose_name = _('Business reward settings')
        verbose_name_plural = _('Business reward settings')

    def __unicode__(self):
        return self.user.get_full_name()


class UserCause(models.Model):
    """
    Relationship between a consumer/user and its selected cause to donate.

    `reward_percent` is the user's chosen percentage. If set, this overrides
                     the user's community default reward. It must lie between
                     the community min and max
    """
    consumer = models.OneToOneField('cyclos.User', verbose_name=_('consumer'))
    cause = models.ForeignKey(
        'cyclos.User', related_name='committed_with', verbose_name=_('cause'))
    donation_percent = models.IntegerField(
        _(u'good causes donation percentage'), null=True, blank=True)

    class Meta:
        ordering = ('consumer__email',)

    @property
    def cause_name(self):
        return self.cause.business_name

    def __unicode__(self):
        return self.consumer.get_full_name()

    def clean(self):
        # check that donation_percent, if set, is within the limits set by
        # the community.
        if self.donation_percent is None:
            return
        community = self.consumer.get_community()
        if community:
            if self.donation_percent > community.max_donation_percent:
                raise ValidationError(_(
                    'Donation percentage must not exceed {0}%'.format(
                        community.max_donation_percent)))
            if self.donation_percent < community.min_donation_percent:
                raise ValidationError(_(
                    'Donation percentage must be at least {0}%'.format(
                        community.min_donation_percent)))


def check_donation_percent_range(sender, instance, created, **kwargs):
    """
    Whenever a Community is saved, check all its members' UserCauses
    and force donation_percent within the configured range
    """
    user_causes = UserCause.objects.filter(
        consumer__cc3_profile__community=instance)
    for user_cause in user_causes.filter(
        donation_percent__gt=instance.max_donation_percent):
        user_cause.donation_percent = instance.max_donation_percent
        user_cause.save()
    for user_cause in user_causes.filter(
        donation_percent__lt=instance.min_donation_percent):
        user_cause.donation_percent = instance.min_donation_percent
        user_cause.save()

post_save.connect(check_donation_percent_range, sender=CC3Community,
                  dispatch_uid='cc3_qoin_community_updated')


class DefaultGoodCause(models.Model):
    """
    Communities using the rewards app need to pick a good cuase
    """
    community = models.ForeignKey('cyclos.CC3Community',
                                  verbose_name=_('community'))
    cause = models.ForeignKey('cyclos.User', related_name='default_good_cause',
                              verbose_name=_('default good cause'))

    class Meta:
        unique_together = ('community', 'cause')

    @property
    def cause_name(self):
        return self.cause.business_name