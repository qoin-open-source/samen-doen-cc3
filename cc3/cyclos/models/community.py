from django.contrib.auth.models import User as AuthUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_countries.fields import CountryField


class CommunityAdmin(models.Model):
    """
    Link between user and community for admin users who do not have a
    cc3_profile.

    A community can have more than one admin.
    A user can only be admin of one community.
    """
    user = models.OneToOneField(AuthUser, related_name='administrator_of')
    community = models.ForeignKey('CC3Community')
    is_default = models.BooleanField(default=False)

    class Meta:
        app_label = 'cyclos'

    def __unicode__(self):
        return u'User: {0} Community: {1}'.format(self.user, self.community)


class CC3Community(models.Model):
    """
    Model for communities.
    """
    MEMBERS_FIRST = '1'
    MEMBERS_ONLY = '2'
    NO_FILTER = '3'
    COMMUNITY_FILTER_OPTIONS = (
        (MEMBERS_FIRST, _('Community members first')),
        (MEMBERS_ONLY, _('Only community members')),
        (NO_FILTER, _('No community filter'))
    )
    DONATION_PERCENTAGE_CHOICES = (
        (0, "0%"),
        (10, "10%"),
        (20, "20%"),
        (30, "30%"),
        (40, "40%"),
        (50, "50%"),
        (60, "60%"),
        (70, "70%"),
        (80, "80%"),
        (90, "90%"),
        (100, "100%"),
    )

    title = models.CharField(
        max_length=255, help_text=_(u'Community title'), unique=True)
    country = CountryField()

    groupsets = models.ManyToManyField(
        'cyclos.CyclosGroupSet', related_name='communities', blank=True)
    community_view = models.CharField(
        max_length=1, choices=COMMUNITY_FILTER_OPTIONS, default=1)
    code = models.CharField(
        max_length=12,
        help_text=u'Used in cyclos, is assigned to each member of this '
                  u'community upon creating the cyclos account. Note that '
                  u'this field should not be confused with '
                  u'"CommunityRegistrationCode", which is a different code '
                  u'for end-users to register with.')
    newreg_notify_cadmin = models.BooleanField(
        _(u'Notify upon registration'), default=True,
        help_text='Notify community administrators when a new user registers')
    profilecomplete_notify_cadmin = models.BooleanField(
        _(u'Notify upon completion of profile'), default=True,
        help_text='Notify community administrators when a new user completes '
                  'their profile')
    transcomplete_notify_cadmin = models.BooleanField(
        _(u'Notify upon completion of transactions'), default=True,
        help_text='Notify community administrators when a user completes a '
                  'transaction')
    negative_balance_warning_buffer = models.IntegerField(
        _(u'Negative balance warning (days)'),
        help_text=_(u'Send negative balance warning emails this many days '
            'before credit term expires'), blank=True, null=True)
    negative_balance_collect_after = models.IntegerField(
        _(u'Negative balance collection after (months)'),
        help_text=_(u'Send negative balance collection emails this many '
            'months after credit term expires'), blank=True, null=True)
    newcampaign_notify_members = models.BooleanField(
        _(u'Email members about new campaigns'), default=False,
        help_text='Email members when a new campaign (activity) is created')
    default_donation_percent = models.IntegerField(
        _(u'Default donation percentage'),
        choices=DONATION_PERCENTAGE_CHOICES, default=40)
    min_donation_percent = models.IntegerField(
        _(u'Minimum donation percentage'),
        choices=DONATION_PERCENTAGE_CHOICES, default=40)
    max_donation_percent = models.IntegerField(
        _(u'Maximum donation percentage'),
        choices=DONATION_PERCENTAGE_CHOICES, default=40)

    class Meta:
        app_label = 'cyclos'
        verbose_name = _(u'community')
        verbose_name_plural = _(u'communities')

    def __unicode__(self):
        return u'{0}'.format(self.title)

    def clean(self):
        # cross-validate the donation percentage fields
        if self.min_donation_percent > self.max_donation_percent:
            raise ValidationError(_(
                'Minimum donation percentage must not exceed maximum'))
        if self.default_donation_percent > self.max_donation_percent:
            raise ValidationError(_(
                'Default donation percentage must not exceed maximum'))
        if self.default_donation_percent < self.min_donation_percent:
            raise ValidationError(_(
                'Default donation percentage must not be less than minimum'))

    def get_groups(self, group_type=None, filter_by_groupset=None):
        """
        Return the CyclosGroups related to this community, optionally with the
        given group_type set.

        :param group_type (str, optional): one of 'initial', 'trial', 'full',
                                           'paid', 'inactive'
        """

        from .group import CyclosGroup

        group_ids = []
        groupsets = self.groupsets.all()
        if filter_by_groupset:
            groupsets = groupsets.filter(id=filter_by_groupset.id)

        for gs in groupsets:
            groups = gs.groups.all()
            if group_type:
                groups = groups.filter(**{group_type: True})
            group_ids += list(groups.values_list('id', flat=True))
        return CyclosGroup.objects.filter(id__in=group_ids)

    def get_initial_groups(self, filter_by_groupset=None):
        return self.get_groups('initial', filter_by_groupset)

    def get_trial_groups(self):
        return self.get_groups('trial')

    def get_full_groups(self):
        return self.get_groups('full')

    def get_paid_groups(self):
        return self.get_groups('paid')

    def get_inactive_groups(self):
        return self.get_groups('inactive')

    def get_administrators(self):
        return self.communityadmin_set.all()

    def get_default_administrator(self):
        """
        Return the user marked as the default administrator OR the first admin
        if none are default.
        """
        administrators = self.communityadmin_set.filter(is_default=True)
        if administrators:
            return administrators[0].user

        all_administrators = self.communityadmin_set.all()
        if all_administrators:
            return all_administrators[0].user

    def get_donation_percent(self):
        return self.default_donation_percent


class CommunityRegistrationCode(models.Model):
    """ code entered in the URL or text box when registering """
    code = models.CharField(max_length=10, unique=True)
    community = models.ForeignKey(CC3Community)
    groupset = models.ForeignKey(
        'cyclos.CyclosGroupSet', blank=True, null=True)

    class Meta:
        app_label = 'cyclos'
        unique_together = ('community', 'groupset')
        verbose_name = _(u'community registration code')

    def __unicode__(self):
        return u'{0} {1}'.format(self.code, self.community.title)
