from decimal import Decimal
import logging

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.forms.models import inlineformset_factory
from django.forms.widgets import Textarea, DateInput
from django.utils.translation import ugettext_lazy as _
from django.template import loader, Context, Template
from django.utils.translation import get_language

from cc3.core.forms import RestrictiveFileField
from cc3.core.models import Category
from cc3.core.widgets import CheckboxSelectMultipleCategoriesTree
from cc3.cyclos.models import CC3Community
from cc3.mail.models import (
    MailMessage, MAIL_TYPE_ENQUIRY_ADMINS,
    MAIL_TYPE_ENQUIRY_ADVERTISER, MAIL_TYPE_ENQUIRY_ENQUIRER)
from .models import (
    Ad, AdImage, AdType, AdPricingOption,
    Campaign, CampaignCategory, CampaignParticipant,
    )
from .common import (AD_DISABLE_CHOICES, AD_STATUS_CHOICES,
                     AD_STATUS_ONHOLD, AD_STATUS_ACTIVE, AD_STATUS_DISABLED)
from .widgets import (
    OfferWantCheckboxSelectMultiple, CommunityCheckboxSelectMultiple,
    PiraatCheckboxSelectMultipleCategoriesTree,
    PiraatCheckboxSelectMultipleCampaignCategoriesTree)

from contact_form.forms import ContactForm
from contact_form.models import Feedback
from tinymce.widgets import TinyMCE


PAGINATE_BY_CHOICES = (
    ('12', '12'),
    ('30', '30'),
    ('60', '60'),
)

SORT_BY_CHOICES = (
    ('date_created__desc', _(u'Most recent')),
    ('price__asc', _(u'Price (ascending)')),
    ('price__desc', _(u'Price (descending)'))
)

attrs_dict = {'class': 'required'}

LOG = logging.getLogger(__name__)


class AdForm(forms.ModelForm):
    DESC_LIMIT = getattr(settings, 'MARKETPLACE_AD_DESCRIPTION_LENGTH', 300)

    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.active(),
        widget=CheckboxSelectMultipleCategoriesTree,
        label=_(u"Categories"),
        required=False
    )

    description = forms.CharField(
        widget=TinyMCE(
            mce_attrs=dict(
                settings.TINYMCE_SIMPLE_CONFIG.items() +
                [('charLimit', DESC_LIMIT)]
            )),
        label=_(u"Description")
    )

    price = forms.DecimalField(
        label=_(u"Price"), max_digits=10, min_value=0.00, decimal_places=2,
        required=False, localize=True)

    price_option = forms.ModelChoiceField(
        required=False,
        queryset=AdPricingOption.objects.all()
    )

    status = forms.ChoiceField(
        choices=AD_DISABLE_CHOICES, required=False,
        label=_(u"Change ad status"))

    class Meta:
        model = Ad
        fields = ('title', 'adtype', 'description', 'price', 'price_option',
                  'category', 'keywords', 'status')

    class Media:
        js = ('js/edit_ad.js',)

    def __init__(self, *args, **kwargs):
        # If prices must be integer, round current price accordingly
        if getattr(settings, 'CC3_CURRENCY_INTEGER_ONLY', False):
            if 'instance' in kwargs and kwargs['instance']:
                kwargs['instance'].price = kwargs['instance'].price.quantize(
                                                                Decimal('1'))
        super(AdForm, self).__init__(*args, **kwargs)

        # If ads need approval, hide the status widget when
        # creating or updating -- It will automatically be set to On Hold
        # Also make On Hold a valid option
        if getattr(settings, 'MARKETPLACE_ADS_NEED_APPROVAL', False):
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['status'].choices = AD_STATUS_CHOICES

        # If prices must be integer, set decimal places on price accordingly
        if getattr(settings, 'CC3_CURRENCY_INTEGER_ONLY', False):
            self.fields['price'].decimal_places = 0

        self.fields['price_option'].widget.attrs.update({
            'class': 'form-control s-selecter'
        })

        # self.fields['price_option'].choices =
        # AdPricingOption.objects.values_list('id', 'title')

    def clean_status(self):
        status = self.cleaned_data['status']
        if self.instance and status:
            if self.instance.status == AD_STATUS_ONHOLD and \
                    status != AD_STATUS_ONHOLD:
                raise forms.ValidationError(
                    _("You are not allowed to change the status of an ad "
                      "that's On Hold."))
        return status

    def clean(self):
        cd = self.cleaned_data
        price = cd.get('price', None)
        price_option = cd.get('price_option', None)
        if ((price is None or price == 0) and price_option is None) or \
                ((price is not None and price != 0) and
                 price_option is not None):
            raise forms.ValidationError(
                _("Either a price or a price option is required."))
        return cd

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')

        if len(desc) > self.DESC_LIMIT:
            raise forms.ValidationError(
                _(u'The description must be shorter than {0} letters.').format(
                    str(self.DESC_LIMIT)))

        return desc

    def clean_price(self):
        """
        Cleans the ``price`` field, making it mandatory only when the project
        has pricing support activated (i.e. it has the ``PRICING_SUPPORT``
        Django setting set to ``True``.
        """
        if settings.PRICING_OPTION_SUPPORT:
            """ Do not validate here, as price option may be used. """
            return self.cleaned_data['price']
        else:
            if settings.PRICING_SUPPORT and not self.cleaned_data['price']:
                raise forms.ValidationError(_(u'Please, enter a price'))

        return self.cleaned_data['price']


class AdToggleStatusForm(forms.ModelForm):
    status = forms.ChoiceField(widget=forms.HiddenInput(),
                               choices=AD_STATUS_CHOICES)

    class Meta:
        model = Ad
        fields = ('status',)

    def clean_status(self):
        if self.instance.status == AD_STATUS_ACTIVE:
            return AD_STATUS_DISABLED
        elif self.instance.status == AD_STATUS_DISABLED:
            return AD_STATUS_ACTIVE
        raise forms.ValidationError(
            _("You are not allowed to change the status of an ad "
              "that's On Hold."))


class AdDisableForm(forms.ModelForm):
    status = forms.ChoiceField(choices=AD_DISABLE_CHOICES)

    class Meta:
        model = Ad
        fields = ('status',)

    def clean_status(self):
        status = self.cleaned_data['status']
        if self.instance and status:
            if self.instance.status == AD_STATUS_ONHOLD and \
                    status != AD_STATUS_ONHOLD:
                raise forms.ValidationError(
                    _("You are not allowed to change the status of an ad "
                      "that's On Hold."))
        return status


class AdImageForm(forms.ModelForm):
    caption = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": _("Enter image title")}))

    class Meta:
        model = AdImage
        fields = ('caption', 'image')


AdImageFormSet = inlineformset_factory(
    Ad, AdImage, form=AdImageForm, extra=1, max_num=4, can_delete=True,
    exclude=('date_created', ))
AdImageUpdateFormSet = inlineformset_factory(
    Ad, AdImage, extra=1, max_num=4, can_delete=True,
    exclude=('date_created', ))


class BusinessFilterForm(forms.Form):
    """
    Form for filtering businesses.

    Special remarks:

        * Categories must be filtered attending two requirements: they are
          activated and they have at least one related ``Ad``. If any of those
          is not accomplished, the ``Category`` must be filtered out and not
          be shown in the frontend.
        * Ad types must be in its ``active`` status.
    """
    paginate_by = forms.ChoiceField(choices=PAGINATE_BY_CHOICES)
    sort_by = forms.ChoiceField(choices=SORT_BY_CHOICES)
    adtype = forms.ModelMultipleChoiceField(
        queryset=AdType.objects.filter(active=True),
        widget=OfferWantCheckboxSelectMultiple, required=False)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.for_businesses(),
        widget=CheckboxSelectMultipleCategoriesTree, required=False)
    community = forms.ModelMultipleChoiceField(
        queryset=CC3Community.objects,
        widget=CommunityCheckboxSelectMultiple, required=False)
    from_price = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, localize=True)
    to_price = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, localize=True)
    # dummy profile_types to be overriden by child projects
    profile_types = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # grab the user object
        super(BusinessFilterForm, self).__init__(*args, **kwargs)


class MarketplaceForm(forms.Form):
    """
    Form for filtering marketplace.

    Special remarks:

        * Categories must be filtered attending two requirements: they are
          activated and they have at least one related ``Ad``. If any of those
          is not accomplished, the ``Category`` must be filtered out and not
          be shown in the frontend.
        * Ad types must be in its ``active`` status.
    """
    paginate_by = forms.ChoiceField(choices=PAGINATE_BY_CHOICES)
    sort_by = forms.ChoiceField(choices=SORT_BY_CHOICES, required=False)
    adtype = forms.ModelMultipleChoiceField(
        queryset=AdType.objects.filter(active=True),
        widget=OfferWantCheckboxSelectMultiple, required=False)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.for_ads(),
        widget=PiraatCheckboxSelectMultipleCategoriesTree, required=False)
    community = forms.ModelMultipleChoiceField(
        queryset=CC3Community.objects,
        widget=CommunityCheckboxSelectMultiple, required=False)
    from_price = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, localize=True)
    to_price = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, localize=True)
    # dummy profile_types to be overriden by child projects
    profile_types = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # grab the user object
        super(MarketplaceForm, self).__init__(*args, **kwargs)


class CampaignFilterForm(forms.Form):
    """
    Cutdown MarketplaceForm for filtering Campaign list

    Special remarks:

        * Categories must be filtered attending two requirements: they are
          visible and they have at least one related ``Campaign``.
          If any of those is not accomplished, the ``Category`` must be
          filtered out and not be shown in the frontend.
        * Ad types must be in its ``active`` status.
    """
    paginate_by = forms.ChoiceField(choices=PAGINATE_BY_CHOICES)
    categories = forms.ModelMultipleChoiceField(
        queryset=CampaignCategory.objects.active(),
        widget=PiraatCheckboxSelectMultipleCampaignCategoriesTree,
        required=False)
    community = forms.ModelMultipleChoiceField(
        queryset=CC3Community.objects,
        widget=CommunityCheckboxSelectMultiple, required=False)


class MarketplaceSearchForm(forms.Form):
    search = forms.CharField(max_length=255)


class MarketplacePayForm(forms.Form):
    """
    Form for making a payment from one user account to another.

    1. Validates that company name is that of the email address
    2. Validates that the amount is less than the users available balance
       (ie balance + credit limit)
    """
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # grab the user object
        super(MarketplacePayForm, self).__init__(*args, **kwargs)

    amount = forms.DecimalField(
        label=_(u"Amount"), max_digits=10, min_value=0.00, decimal_places=2,
        error_messages={'required': _(u'Please an amount to pay')},
        localize=True)
    contact_name = forms.CharField(
        widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=255)),
        label=_(u'Contact Name <br />(business)'),
        error_messages={'required': _(u'Please enter the Contact Name at the '
                                      u'company you wish to pay')})
    description = forms.CharField(
        widget=Textarea, label=_(u"Description"),
        error_messages={'required': _(u'Please enter a description for the '
                                      u'payment')},
        required=False)
    ad = forms.IntegerField(widget=forms.HiddenInput())

    def clean_amount(self):
        from cc3.cyclos import backends

        # NB need to use availableBalance here really - as overdrafts are
        # possible.
        available_balance = backends.get_account_status(
            self.user.username).accountStatus.availableBalance
        if self.cleaned_data['amount'] > available_balance:
            raise forms.ValidationError(
                _(u'You do not have sufficient credit to complete the payment'))
        return self.cleaned_data['amount']

    def clean(self):
        from cc3.cyclos.models import CC3Profile
        cleaned_data = super(MarketplacePayForm, self).clean()
        contact_name = cleaned_data.get('contact_name', None)

        if contact_name:
            # check the email and business name are for the same user
            try:
                # brittle way of getting business name from bracketed string
                # could break if businesses have brackets in their name?
                contact_name_business_name = contact_name[
                    contact_name.index("(") + 1:contact_name.rindex(")")]
                if contact_name_business_name:
                    CC3Profile.viewable.get(
                        business_name__iexact=contact_name_business_name)
            except CC3Profile.DoesNotExist:
                raise forms.ValidationError(_(u'Please check the company name'))

        return self.cleaned_data


class WantContactForm(ContactForm):
    # Sending of emails when someone enquires about an Ad. (Somewhat
    # complicated for reasons of backward compatibility):
    # enquirer and advertiser emails:
    #  if the mail_type templates exist in the database, use those,
    #  but fall back to template files if not
    # admin emails:
    #  if the template exists in the database, use that; if not, don't send
    #  emails to admins
    enquirer_subject_template_name = 'marketplace/' \
                                     'enquire_enquirer_email_subject.txt'
    enquirer_template_name = 'marketplace/enquire_enquirer_email.txt'
    advertiser_subject_template_name = 'marketplace/' \
                                       'enquire_advertiser_email_subject.txt'
    advertiser_template_name = 'marketplace/enquire_advertiser_email.txt'
    enquirer_mail_type = MAIL_TYPE_ENQUIRY_ENQUIRER
    advertiser_mail_type = MAIL_TYPE_ENQUIRY_ADVERTISER
    admins_mail_type = MAIL_TYPE_ENQUIRY_ADMINS

    ad_id = forms.IntegerField(widget=forms.HiddenInput())
    name = forms.CharField(
        max_length=100, widget=forms.TextInput(attrs=attrs_dict),
        label=_(u"Advertiser's name"))
    email = forms.EmailField(
        widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=200)),
        label=_(u'Your email address'))
    body = forms.CharField(
        widget=Textarea, label=_(u'Any comments about the enquiry?'),
        required=False)

    def __init__(self, *args, **kwargs):
        super(WantContactForm, self).__init__(*args, **kwargs)
        try:
            self.enquirer_msg = MailMessage.objects.get_msg(
                MAIL_TYPE_ENQUIRY_ENQUIRER, lang=get_language())
        except MailMessage.DoesNotExist:
            self.enquirer_msg = None
        try:
            self.advertiser_msg = MailMessage.objects.get_msg(
                MAIL_TYPE_ENQUIRY_ADVERTISER, lang=get_language())
        except MailMessage.DoesNotExist:
            self.advertiser_msg = None
        try:
            self.admins_msg = MailMessage.objects.get_msg(
                MAIL_TYPE_ENQUIRY_ADMINS, lang=get_language())
        except MailMessage.DoesNotExist:
            self.admins_msg = None

    def enquirer_message(self):
        context = self.get_context()
        # the enquirer isn't the form name, it's the user sending the message
        context['name'] = self.request.user.get_profile().full_name
        if self.enquirer_msg:
            return Template(self.enquirer_msg.body).render(Context(context))
        return loader.render_to_string(
            self.enquirer_template_name, context)

    def enquirer_subject(self):
        if self.enquirer_msg:
            return Template(self.enquirer_msg.subject).render(
                Context(self.get_context()))
        enquirer_subject = loader.render_to_string(
            self.enquirer_subject_template_name, self.get_context())
        return ''.join(enquirer_subject.splitlines())

    def advertiser_message(self):
        if self.advertiser_msg:
            return Template(self.advertiser_msg.body).render(
                Context(self.get_context()))
        if callable(self.advertiser_template_name):
            advertiser_template_name = self.advertiser_template_name
        else:
            advertiser_template_name = self.advertiser_template_name
        return loader.render_to_string(advertiser_template_name,
                                       self.get_context())

    def advertiser_subject(self):
        if self.advertiser_msg:
            return Template(self.advertiser_msg.subject).render(
                Context(self.get_context()))
        advertiser_subject = loader.render_to_string(
            self.advertiser_subject_template_name, self.get_context())
        return ''.join(advertiser_subject.splitlines())

    def get_context(self):
        context = super(WantContactForm, self).get_context()
        context['ad'] = Ad.objects.get(pk=self.cleaned_data['ad_id'])
        context['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")
        # need these for the db templates
        context['site'] = Site.objects.get_current()
        if self.request.user.is_authenticated():
            context['enquirer'] = self.request.user.get_profile()
        else:
            context['enquirer'] = self.cleaned_data['email']
        context['advertiser'] = context['ad'].created_by.user.get_profile()
        return context

    '''
    Override the clean method to validate the body field and make sure it is not empty.
    '''
    def clean(self):
        body = self.cleaned_data.get('body')
        if not body:
            self._errors['body'] = self.error_class([_(
                u'This field is required.')])
            del self.cleaned_data['body']
        return self.cleaned_data

    def save(self, fail_silently=False):
        # don't use base save - no need to email site admins
        ad = Ad.objects.get(pk=self.cleaned_data['ad_id'])
        advertiser_subject = self.advertiser_subject()
        advertiser_message = self.advertiser_message()
        advertiser_email = ad.created_by.user.email

        fb = Feedback(
            name=advertiser_subject[:100],
            email=advertiser_email,
            body=advertiser_message,
        )
        if self.request.user.is_authenticated():
            fb.user = self.request.user
        fb.save()

        advertiser_message_dict = {
            'from_email': self.from_email,
            'subject': advertiser_subject,
            'recipient_list': [advertiser_email],
            'message': advertiser_message,
        }
        send_mail(fail_silently=fail_silently, **advertiser_message_dict)

        # send email to enquirer
        enquirer_message_dict = {
            'from_email': self.from_email,
            'subject': self.enquirer_subject(),
            'recipient_list': [self.cleaned_data['email']],
            'message': self.enquirer_message(),
        }
        send_mail(fail_silently=fail_silently, **enquirer_message_dict)

        if self.admins_msg:
            for comm_admin in ad.created_by.community.get_administrators():
                context = self.get_context()
                try:
                    self.admins_msg.send(comm_admin.user.email, context)
                except Exception as e:
                    LOG.error(
                        'Failed to send enquiry email to community admin {0}: '
                        '{1}'.format(comm_admin.pk, e))


class CampaignForm(forms.ModelForm):
    DESC_LIMIT = getattr(settings, 'MARKETPLACE_AD_DESCRIPTION_LENGTH', 300)

    categories = forms.ModelMultipleChoiceField(
        queryset=CampaignCategory.objects.active(),
        widget=CheckboxSelectMultipleCategoriesTree,
        label=_(u"Categories"),
        error_messages={
            'required': _(u'Please select at least one category')
            },
        required=True
    )
    communities = forms.ModelMultipleChoiceField(
        queryset=CC3Community.objects,
        widget=CommunityCheckboxSelectMultiple,
        label=_(u"Communities"),
        error_messages={
            'required': _(u'Please select at least one community')
            },
        required=True
    )
    description = forms.CharField(
        widget=TinyMCE(
            mce_attrs=dict(
                settings.TINYMCE_SIMPLE_CONFIG.items() +
                [('charLimit', DESC_LIMIT)]
            )),
        label=_(u"Description")
    )
    picture = RestrictiveFileField(
        required=False,
        valid_file_formats=['jpg', 'png', 'gif', 'jpeg'])

    class Meta:
        model = Campaign
        fields = ('title', 'criteria', 'image', 'communities',
                  'start_date', 'start_time', 'end_time',
                  'description', 'categories',
                  'max_participants', 'reward_per_participant',
                  'contact_name', 'contact_telephone', 'contact_email',
                  'address', 'postal_code', 'city', 'country',
                  'extra_address', 'num_street',
                  )

    class Media:
        js = ('js/edit_ad.js',)

    def __init__(self, *args, **kwargs):
        super(CampaignForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update(
            {
                'placeholder': self.fields['title'].help_text,
            })
        self.fields['start_date'].widget.attrs.update(
            {
                'placeholder': "dd-mm-yyyy",
            })
        self.fields['start_time'].widget.attrs.update(
            {
                'placeholder': "hh:mm",
            })
        self.fields['end_time'].widget.attrs.update(
            {
                'placeholder': "hh:mm",
            })
        currency_name = getattr(settings, 'CURRENCY_NAME', 'punten')
        self.fields['reward_per_participant'].widget.attrs.update(
            {
                'placeholder': _(
                    u'Number of {0} per person').format(currency_name),
            })
        self.fields['max_participants'].widget.attrs.update(
            {
                'placeholder': _(u'Number of participants'),
            })

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        if len(desc) > self.DESC_LIMIT:
            raise forms.ValidationError(
                _(u'The description must be shorter than {0} letters.').format(
                    str(self.DESC_LIMIT)))
        return desc

    def clean_reward_per_participant(self):
        reward_per_participant = self.cleaned_data.get(
            'reward_per_participant', '')
        if not reward_per_participant > 0:
            raise forms.ValidationError(
                _(u'The reward must be > 0'))
        if getattr(settings, 'CC3_CURRENCY_INTEGER_ONLY', False):
            if not int(reward_per_participant) == reward_per_participant:
                raise forms.ValidationError(
                    _(u'The reward must be an integer amount'))
        return reward_per_participant


class CampaignSignupForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ('id',)


class CancelCampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ('why_cancelled',)


class RemoveCampaignParticipantForm(forms.ModelForm):
    why_removed = forms.CharField(widget=Textarea, required=False)

    class Meta:
        model = CampaignParticipant
        fields = ('why_removed', )


class RewardCampaignParticipantForm(forms.ModelForm):

    class Meta:
        model = CampaignParticipant
        fields = ('start_time', 'end_time')

    def clean(self):
        """Cross-validate start_ and end_time:

        Either
        - Both null
        or
        - Both non-null, and start_time <= end_time
        """
        cd = self.cleaned_data
        start_time = cd.get('start_time', None)
        end_time = cd.get('end_time', None)
        if start_time and end_time:
            if start_time > end_time:
                raise forms.ValidationError(
                    _("From must be before To"))
        elif start_time or end_time:
            raise forms.ValidationError(
                _("Must supply both From and To (or leave both blank)"))
        return cd
