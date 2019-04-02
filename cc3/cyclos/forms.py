import logging
import re

from django import forms
from django.conf import settings
from django.utils.translation import ugettext, ugettext_lazy as _

from cc3.core.widgets import CheckboxSelectMultipleCategoriesTree
from cc3.core.models import Category
from .models import CC3Profile

LOG = logging.getLogger('cc3.cyclos.forms')

DEFAULT_PHONE_REGEX = r'^[\d\(\)\+]*$'

kvk_re = re.compile(r'\d{8}')


class CC3ProfileForm(forms.ModelForm):
    # In case of changing email credential in future - here's the def from the
    # registration form.
    #    email = forms.EmailField(widget=forms.TextInput(
    #        attrs=dict(attrs_dict, maxlength=75)), label=_(u'Email Address'),
    #        error_messages={'required': _(u'Please enter your Email address')}
    #    )

    # TODO: add in 'email_new_camapaigns' if needed by any projects
    # (currently only Troeven which has custom versions of these forms)

    categories = forms.ModelMultipleChoiceField(
        label=_(u'Offer Categories'),
        queryset=Category.objects.active(),
        widget=CheckboxSelectMultipleCategoriesTree)

    want_categories = forms.ModelMultipleChoiceField(
        label=_(u'Want Categories'),
        queryset=Category.objects.active(),
        widget=CheckboxSelectMultipleCategoriesTree)

    class Meta:
        model = CC3Profile
        fields = (
            'community', 'picture', 'first_name', 'last_name', 'business_name',
            'job_title', 'country', 'city', 'address', 'postal_code',
            'phone_number', 'mobile_number', 'company_website', 
            'company_description', 'is_visible', 'is_approved', 
            'categories', 'want_categories', 'email_category_matches',
        )

        widgets = {
            'community': forms.Select(attrs={'disabled': 'disabled'}),
        }

    class Media:
        js = ['js/profile_form.js']

    def __init__(self, *args, **kwargs):
        self.caller = kwargs.pop('user', None)

        super(CC3ProfileForm, self).__init__(*args, **kwargs)

        # mobile_number is required iff MOBILE_NUMBER_MANDATORY is True
        self.fields['mobile_number'].required = getattr(
                                settings, 'MOBILE_NUMBER_MANDATORY', True)

        # registration_number is only included in the profile form if
        # KVK_NUMBER_IN_PROFILE setting is True (defaults to False)
        #if not getattr(settings, 'KVK_NUMBER_IN_PROFILE', False):
        #    del self.fields['registration_number']
        #else:
        #    self.fields['registration_number'].required = True

        self.caller_is_admin = False
        if self.caller:
            if self.caller.is_superuser:
                self.caller_is_admin = True
            elif self.instance:
                if self.caller.get_admin_community() == self.instance.community:
                    self.caller_is_admin = True

        # Remove the 'is_approved' flag unless
        # a) admins need to approve visibility for this site
        # and
        # b) the caller is community admin
        if not (getattr(settings, 'ADMINS_APPROVE_PROFILES', False) and
                self.caller_is_admin):
            del self.fields['is_approved']

        # If is_visible shouldn't be changed, hide it
        # (Template can show dummy disabled checkbox if wanted)
        if getattr(settings, 'ADMINS_APPROVE_PROFILES', False):
            if not self.caller_is_admin and not self.instance.is_approved:
                self.fields['is_visible'].widget = forms.HiddenInput()

        # remove the want_categories field unless required for this site
        if not getattr(settings, 'WANT_CATEGORIES_IN_PROFILE', False):
            del self.fields['want_categories']

        # remove the email_category_matches field unless required for this site
        if not getattr(settings, 'TRACK_PROFILE_CATEGORIES', False):
            del self.fields['email_category_matches']

    def clean_first_name(self):
        data = self.cleaned_data.get('first_name', '').strip()
        if not data:
            raise forms.ValidationError(_("Please enter your First Name"))

        maxlen = getattr(settings,
                         'PROFILE_FORMS_MAX_LENGTH_FIRST_NAME', None)
        if maxlen and len(data) > maxlen:
            raise forms.ValidationError(
                _('Please enter a {1} of {0} or fewer characters').format(
                    maxlen, ugettext(self.fields['first_name'].label)))

        return data

    def clean_last_name(self):
        data = self.cleaned_data.get('last_name', '').strip()
        if not data:
            raise forms.ValidationError(_("Please enter your Last Name"))

        maxlen = getattr(settings,
                         'PROFILE_FORMS_MAX_LENGTH_LAST_NAME', None)
        if maxlen and len(data) > maxlen:
            raise forms.ValidationError(
                _('Please enter a {1} of {0} or fewer characters').format(
                    maxlen, ugettext(self.fields['last_name'].label)))

        return data

    def clean_business_name(self):
        data = self.cleaned_data.get('business_name', '').strip()
        if not data:
            raise forms.ValidationError(_("Please enter your Business Name"))

        maxlen = getattr(settings,
                         'PROFILE_FORMS_MAX_LENGTH_BUSINESS_NAME', None)
        if maxlen and len(data) > maxlen:
            raise forms.ValidationError(
                _('Please enter a {1} of {0} or fewer characters').format(
                    maxlen, ugettext(self.fields['business_name'].label)))

        return data

    def clean_address(self):
        data = self.cleaned_data.get('address', '').strip()
        if not data:
            raise forms.ValidationError(_("Please enter your Address"))

        return data

    def clean_phone_number(self):
        data = self.cleaned_data.get('phone_number', '').strip()
        # remove internal spaces
        data = ''.join(data.split())
        if data:
            phone_re = re.compile(getattr(settings, 'CUSTOM_PHONE_REGEX',
                                  DEFAULT_PHONE_REGEX))
            if not phone_re.match(data):
                error_msg = _("Please enter a valid Phone Number")
                extra_msg = getattr(settings, 'CUSTOM_PHONE_REGEX_DESC', None)
                if extra_msg:
                    error_msg += u" ({0})".format(extra_msg)
                raise forms.ValidationError(error_msg)

        return data

    def clean_mobile_number(self):
        data = self.cleaned_data.get('mobile_number', '').strip()
        # remove internal spaces
        data = ''.join(data.split())
        if getattr(settings, 'MOBILE_NUMBER_MANDATORY', True):
            if not data:
                raise forms.ValidationError(
                    _("Please enter your Mobile Number"))

            if getattr(settings, 'MOBILE_NUMBER_MIN_LENGTH', None):
                if len(data.strip()) < settings.MOBILE_NUMBER_MIN_LENGTH:
                    raise forms.ValidationError(
                        _('Please enter a mobile number of at least {0} '
                          'digits'.format(settings.MOBILE_NUMBER_MIN_LENGTH)))

            if getattr(settings, 'MOBILE_NUMBER_MAX_LENGTH', None):
                if len(data.strip()) > settings.MOBILE_NUMBER_MAX_LENGTH:
                    raise forms.ValidationError(
                        _('Please enter a mobile number of at most {0} '
                          'digits'.format(settings.MOBILE_NUMBER_MAX_LENGTH)))

        # only validate number is there is one
        if data:
            mobile_re = re.compile(getattr(settings, 'CUSTOM_MOBILE_REGEX',
                                           DEFAULT_PHONE_REGEX))
            if not mobile_re.match(data):
                error_msg = _("Please enter a valid Mobile Number")
                extra_msg = getattr(settings, 'CUSTOM_MOBILE_REGEX_DESC', None)
                if extra_msg:
                    error_msg += u" ({0})".format(extra_msg)
                raise forms.ValidationError(error_msg)

        return data

    def clean_community(self):
        """
        Don't allow community to be changed the widget is disabled anyway but
        put this here just in case anyone tries to hack.
        """
        return self.instance.community

    def clean_is_visible(self):
        # If profile isn't approved only admins can change this,
        # so return the old value for non-admin users in this case
        if not self.instance.is_approved and not self.caller_is_admin:
            return self.instance.is_visible
        return self.cleaned_data.get('is_visible')

    def clean(self):
        cleaned_data = super(CC3ProfileForm, self).clean()

        first_name = cleaned_data.get('first_name', u'').strip()
        last_name = cleaned_data.get('last_name', u'').strip()
        business_name = cleaned_data.get('business_name', u'').strip()

        if not first_name and not last_name and not business_name:
            raise forms.ValidationError(_("Please check the form for errors"))

        # Always return the full collection of cleaned data.
        return cleaned_data


class CC3ProfileDisplayForm(forms.ModelForm):
    """
    Form used to display profile data to the user. Should not be used for
    updating data.
    """
    extra_attrs = {'class': "input-text large", 'disabled': True}

    def __init__(self, *args, **kwargs):
        super(CC3ProfileDisplayForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update(
                CC3ProfileDisplayForm.extra_attrs)

    class Meta:
        model = CC3Profile
        fields = (
            'address', 'city', 'postal_code',
        )

    def clean(self):
        # As this form is read-only raise an error.
        raise NotImplementedError
