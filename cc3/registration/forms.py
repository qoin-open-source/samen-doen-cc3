from django import forms
from django.utils.translation import ugettext_lazy as _

from cc3.cyclos.models import CommunityRegistrationCode
from cc3.cyclos.models import User

attrs_dict = {'class': 'required'}

REGISTRATION_TYPE_CHOICES = (('C', _('Business'),), ('I', _('Individual'),))


class BaseRegistrationForm(forms.Form):
    """
    Form for registering a new TradeQoin user account.
    
    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.
    
    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend.

    Form for initial registration on the Trade Qoin system
    """    
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs=dict(attrs_dict, maxlength=75,
                       placeholder=_(u'Email Address'))),
        label=_(u'Email Address'),
        error_messages={'required': _(u'Please enter your Email address')})
    email_confirmation = forms.EmailField(
        widget=forms.TextInput(
            attrs=dict(attrs_dict, maxlength=75,
                       placeholder=_(u'Confirm Email'))),
        label=_(u'Email Address (again)'),
        error_messages={'required': _(u'Please confirm your Email address')})

    reg_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs=dict(attrs_dict, render_value=False,
                       placeholder=_(u'Password'))),
        label=_(u"Password"),
        error_messages={'required': _(u'Please enter your chosen password')})
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput(
            attrs=dict(attrs_dict, render_value=False,
                       placeholder=_(u'Confirm Password'))),
        label=_(u"Password (again)"),
        error_messages={'required': _(u'Please confirm your chosen password')})

    tandc_confirmation = forms.BooleanField(
        label=_(u"I've read and accepted the terms &amp; conditions"),
        required=True,
        error_messages={
            'required': _(u'You must accept the terms & conditions to '
                          u'register')})

    community_code = forms.CharField(
        widget=forms.TextInput(
            attrs=dict(attrs_dict, maxlength=75,
                       placeholder=_(u'Community Code'))),
        label=_(u'Community Code'), required=False)

    # Optional field to allow the community admin add member wizard to activate
    # the account immediately.
    activate_immediately = forms.BooleanField(
        label=_(u"Activate account immediately?"),
        help_text=_("Ticking this box activates the new account immediately "
                    "and will not send the user an activation email."),
        required=False,
        error_messages={
            'required': _(u'You must accept the terms & conditions to '
                          u'register')})

    def clean_email(self):
        from cc3.cyclos.utils import check_cyclos_account

        # Validate that email doesn't already exist in Cyclos.
        validation_message = check_cyclos_account(self.cleaned_data['email'])
        if validation_message:
            raise forms.ValidationError(validation_message)

        # Validate that the email doesn't already exist in Django.
        try:
            User.objects.get(email=self.cleaned_data['email'])
            raise forms.ValidationError(
                _(u'This email has already been registered'))
        except User.DoesNotExist:
            pass

        return self.cleaned_data['email']

    def clean_community_code(self):
        if self.cleaned_data['community_code'] and self.cleaned_data['community_code'].strip() != '':
            try:
                CommunityRegistrationCode.objects.get(
                    code=self.cleaned_data['community_code'])
            except CommunityRegistrationCode.DoesNotExist:
                raise forms.ValidationError(
                    _(u"Please enter a valid community code."))

        return self.cleaned_data['community_code']

    def clean_reg_password(self):
        from cc3.accounts.utils import has_numbers
        data = self.cleaned_data['reg_password']
        
        if len(data) < 8:
            raise forms.ValidationError(
                _(u"Please enter a password that is at least 8 characters "
                  u"long."))
        
        if not has_numbers(data, 1):
            raise forms.ValidationError(
                _(u"Please enter a password that contains at least 1 number."))
        
        return data

    # #2014 Display email address and password-related errors on top of the affected form fields
    def clean(self):
        cleaned_data = super(BaseRegistrationForm, self).clean()

        # Handle the email fields
        email = cleaned_data.get('email', None)
        email_confirmation = cleaned_data.get('email_confirmation', None)
        if email and email_confirmation and (email != email_confirmation):
            self.add_error('email', forms.ValidationError(
                _(u'Please enter the same email for both email and email '
                  u'confirmation.')))
            self.add_error('email_confirmation', forms.ValidationError(''))

        # Handle the password fields
        password = cleaned_data.get('reg_password', None)
        password_confirmation = cleaned_data.get(
            'password_confirmation', None)
        if password and password_confirmation and (password != password_confirmation):
            self.add_error('reg_password', forms.ValidationError(
                _(u'Please enter the same password for both password and password confirmation.')))
            self.add_error('password_confirmation', forms.ValidationError(''))
        return self.cleaned_data


class TradeQoinRegistrationForm(BaseRegistrationForm):
    pass


class SoNantesRegistrationForm(forms.Form):
    registration_type = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=REGISTRATION_TYPE_CHOICES,
        error_messages={
            'required': _('Please select Individual or Entreprise')
        }
    )


class BrixtonRegistrationForm(forms.Form):
    registration_type = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=REGISTRATION_TYPE_CHOICES,
        error_messages={
            'required': _('Please select Business or Individual')
        }
    )


class QoinWareRegistrationForm(BaseRegistrationForm):
    pass
