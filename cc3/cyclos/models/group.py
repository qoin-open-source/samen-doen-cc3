from django.conf import settings
from django.db import models


class CyclosGroup(models.Model):
    """ mirrors the groups in cyclos """
    id = models.IntegerField(
        primary_key=True,
        help_text='ID of a CyclosGroup must be the same as an existing group '
                  'in Cyclos, this field is not auto-incremented')
    name = models.CharField(max_length=255, unique=True)
    permit_split_payments_in_euros = models.BooleanField(
        default=False,
        help_text='Split payments, specifically for the BYB group '
                  '(implemented)')
    initial = models.BooleanField(
        default=False,
        help_text='This is the group to use when a member self-registers '
                  '(implemented)')
    trial = models.BooleanField(
        default=False,
        help_text='This group has no joining fee but may have restricted '
                  'functionality (not implemented)')
    full = models.BooleanField(
        default=True,
        help_text='This group does not have restricted functionality '
                  '(implemented)')
    paid = models.BooleanField(
        default=False,
        help_text='Members cannot be moved to this group without a fee being'
                  ' paid or invoiced (not implemented)')
    inactive = models.BooleanField(
        default=False,
        help_text='A group that members are moved to when they have left the'
                  ' scheme, members in this group will not be shown publicly'
                  ' or be able to log in, so the auth_user is_active flag '
                  'should be disabled as well (not implemented)')

    send_notification = models.BooleanField(
        default=False,
        help_text='Send a notification when a community admin changes a user '
                  'to this group')
    visible_to_all_communities = models.BooleanField(
        default=False,
        help_text='If true, profiles with this cyclos group set should be '
                  'visible to all communities'
    )

    initial_products = models.ManyToManyField(
        'billing.Product', blank=True, related_name='assign_to_groups',
        help_text='Auto-assigned to new users belonging to this group')

    ### Auto-invoice fields ###
    create_monthly_invoice = models.BooleanField(
        default=False,
        help_text=u'Automatically create a monthly invoice for these users. '
                  u'Note: ensure that users in the groupset may view invoices.')
    create_activation_invoice = models.BooleanField(
        default=False,
        help_text=u'Automatically create an invoice upon activation of a user')
    invoice_currency = models.ForeignKey(
        'invoices.Currency', blank=True, null=True,
        help_text=u'The currency to be used for automatically created invoices'
                  u'. Mandatory if "create monthly invoice" is enabled.')
    invoice_user = models.ForeignKey(
        'cyclos.User', verbose_name=u'Invoice sender', blank=True, null=True,
        help_text=u'The user from which automatic invoices are sent. Mandatory'
                  u' if "create monthly invoice" is enabled.')
    invoice_day_otm = models.IntegerField(
        verbose_name='Invoice day of the month', default=1,
        help_text=u'Day of the month that automatic monthly invoices are sent')
    invoice_monthly_amount = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True,
        help_text=u'Amount to be automatically invoiced each month. If not '
                  u'specified AUTO_INVOICE_AMOUNT will be used from the '
                  u'project settings to determine this value')
    invoice_monthly_description = models.CharField(
        max_length=255, blank=True,
        help_text=u'Description added to the invoice about the monthly payment')

    invoice_activation_amount = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True,
        help_text=u'Amount to be automatically invoiced upon activation. If '
                  u'not specified AUTO_INVOICE_AMOUNT will be used from the '
                  u'project settings to determine this value')
    invoice_activation_description = models.CharField(
        max_length=255, blank=True,
        help_text=u'Description added to the invoice about the activation '
                  u'payment')
    ### ###

    class Meta:
        app_label = 'cyclos'

    def __unicode__(self):
        return self.name

    def groupsets_display(self):
        """ Used to display the GroupSets in the admin list-view """
        return u", ".join([gs.name for gs in self.groupsets.all()])
    groupsets_display.short_description = u'Group sets'

    def communities_display(self):
        """ Used to display the Communitiies in the admin list-view """
        return u", ".join(
            [gs.communities_display() for gs in self.groupsets.all()])
    communities_display.short_description = u'Communities'

    @property
    def is_business_group(self):
        return self.name == getattr(settings, 'CYCLOS_BUSINESS_MEMBER_GROUP', None)

    @property
    def is_institution_group(self):
        return self.name == getattr(settings, 'CYCLOS_INSTITUTION_MEMBER_GROUP', None)

    @property
    def is_charity_group(self):
        return self.name == getattr(settings, 'CYCLOS_CHARITY_MEMBER_GROUP', None)

    @property
    def is_consumer_group(self):
        return (self.name in getattr(settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', []))


class CyclosGroupSet(models.Model):
    """
    A collection of CyclosGroups with a specific workflow in Cyclos.
    """
    name = models.CharField(max_length=255, unique=True)
    prefix = models.CharField(
        max_length=10, blank=True, unique=True,
        help_text=u'If provided, the account number is prefixed with the value'
                  u' in this field')
    slug = models.SlugField(
        blank=True,
        help_text=u"Used to identify this groupset in project-specific views "
                  u"and templates. For SoNantes, set this to 'company' or "
                  u"'individual'")
    groups = models.ManyToManyField(
        CyclosGroup, blank=True, related_name='groupsets')  # null=True,
    is_visible = models.BooleanField(
        default=True,
        help_text=u'If the profiles with this groupset are visible in the '
                  u'marketplace business-view')
    may_add_ads = models.BooleanField(
        default=True,
        help_text=u'If the users within this groupset may add ads via the '
                  u'account side-menu')
    may_view_invoices = models.BooleanField(
        default=True,
        help_text=u'If the users within this groupset may view their '
                  u'invoices via the account side-menu')
    is_business = models.BooleanField(
        default=False, help_text=u'If the users within this groupset may be '
                                 u'linked with terminals and create operators '
                                 u'for dealing with card transactions')

    class Meta:
        app_label = 'cyclos'

    def __unicode__(self):
        return self.name

    def groups_display(self):
        """ Used to display the CyclosGroups in the admin list-view """
        return u", ".join([group.name for group in self.groups.all()])
    groups_display.short_description = u'Groups'

    def communities_display(self):
        """ Used to display the Communities in the admin list-view """
        return u", ".join([comm.title for comm in self.communities.all()])
    communities_display.short_description = u'Communities'
