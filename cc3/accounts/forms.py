import datetime
import logging

from django import forms
from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.core.mail import send_mail
from django.forms.widgets import Textarea
from django.template import loader
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from contact_form.forms import ContactForm
from contact_form.models import Feedback

from cc3.accounts.utils import check_amount
from cc3.accounts.widgets import ToggleSelectMultiple
from cc3.cyclos import backends
from cc3.cyclos.models import CC3Profile, CyclosChannel
from .utils import has_numbers

LOG = logging.getLogger(__name__)

attrs_dict = {'class': 'required'}


class CC3SetPasswordForm(SetPasswordForm):
    def clean_new_password1(self):
        data = self.cleaned_data.get('new_password1')

        if len(data) < 8:
            raise forms.ValidationError(
                _(u'Please enter a password that is at least 8 characters '
                  u'long.'))

        if not has_numbers(data, 1):
            raise forms.ValidationError(
                _(u'Please enter a password that contains at least 1 number.'))

        return data


class CC3PasswordChangeForm(PasswordChangeForm):
    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Your old password was entered incorrectly. "
                                "Please enter it again."),
    })
    old_password = forms.CharField(
        label=_("Old password"), widget=forms.PasswordInput)

    new_password1 = forms.CharField(
        label=mark_safe('{0} <a href="#" class="element tp" title="{1}">'
                        '</a>'.format(_("New password"),
                                      _(u"The password must contain at least 8"
                                        u" character and include a number"))),
        widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"),
                                    widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super(CC3PasswordChangeForm, self).__init__(*args, **kwargs)

        self.fields.get('old_password').error_messages['required'] = _(
            u'the current password is required')
        self.fields.get('new_password1').error_messages['required'] = _(
            u'the new password is required')
        self.fields.get('new_password2').error_messages['required'] = _(
            u'the new password confirmation is required')

    def clean_new_password1(self):
        data = self.cleaned_data.get('new_password1')
        old = self.cleaned_data.get('old_password')

        if old == data:
            raise forms.ValidationError(
                _(u'The new password must be different'))

        if len(data) < 8:
            raise forms.ValidationError(
                _(u'Please enter a password that is at least 8 characters '
                  u'long.'))

        if not has_numbers(data, 1):
            raise forms.ValidationError(
                _(u'Please enter a password that contains at least 1 number.'))

        return data


class CC3ProfileChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return u"{} {}".format(obj.first_name, obj.last_name)


class TradeQoinPayDirectForm(forms.Form):
    """
    Form for making a payment from one user account to another.

    1. Validates that company name is that of the email address
    2. Validates that the amount is less than the users available balance (ie
    balance + credit limit).
    """

    # moved away from constant at start of file, as tests broke
    # (ie ignored settings overrides)
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # Cache the user object you pass in
        # And carry on to init the form.
        super(TradeQoinPayDirectForm, self).__init__(*args, **kwargs)

    # NB need dynamic way of specifying max amount (ie current balance / credit
    # limit of user).
    amount = forms.DecimalField(
        label=_(u'Amount'),
        help_text=_(u"Amount to pay"),
        max_digits=10, min_value=getattr(
            settings, 'CC3_CURRENCY_MINIMUM', 0.01),
        decimal_places=2,
        error_messages={'required': _(u'Please enter an amount to pay')},
        localize=True)
    contact_name = forms.CharField(
        widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=255)),
        label=_(u'Contact Name <br />(business)'),
        help_text=_(u'Person to contact'),
        error_messages={
            'required': _(u'Please enter the Contact Name at the company you '
                          u'wish to pay')
        })
    profile = CC3ProfileChoiceField(
        queryset=CC3Profile.viewable.all().order_by('first_name', 'last_name'),
        widget=forms.HiddenInput(),
        error_messages={
            'required': '',
        })
    description = forms.CharField(
        widget=Textarea, label=_(u"Description"),
        help_text=_(u'Give a clear description of the payment'),
        error_messages={
            'required': _(u'Please enter a description for the payment')
        },
        max_length=180, required=False)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        return check_amount(amount, self.user.username)

    def clean_profile(self):
        profile = self.cleaned_data.get('profile')
        pending_can_pay = getattr(
            settings, 'CYCLOS_PENDING_MEMBERS_CAN_PAY', True)

        if not profile.has_full_account() and not pending_can_pay:
            raise forms.ValidationError(
                _(u'You cannot pay this member as their account is still '
                  u'pending.'))
        return profile

    def clean(self):
        cleaned_data = super(TradeQoinPayDirectForm, self).clean()
        profile = cleaned_data.get('profile')
        contact_name = cleaned_data.get('contact_name')
        if contact_name and not profile:
            raise forms.ValidationError(
                _(u'You have not selected a valid recipient for your payment'))
        return cleaned_data


class TradeQoinSplitPayDirectForm(TradeQoinPayDirectForm):
    """
    For use by members with CyclosGroup.permit_split_payments_in_euros enabled,
    this form allows members to also add a total value, separate from the
    number of TQ.
    """
    total_value = forms.DecimalField(
        label=_(u"Total value of this trade"),
        max_digits=10, min_value=getattr(
            settings, 'CC3_CURRENCY_MINIMUM', 0.01), decimal_places=2,
        required=False)

    def clean(self):
        cleaned_data = super(TradeQoinSplitPayDirectForm, self).clean()
        total_value = cleaned_data.get('total_value', None)
        amount = cleaned_data.get('amount', None)
        if total_value and amount:
            if total_value < amount:
                raise forms.ValidationError(
                    _(u'Total value may not be less than the number of '
                      u'{0}s').format(getattr(
                          settings, "CC3_SYSTEM_NAME", "TradeQoin"))
                )
        return cleaned_data


class TransactionsSearchForm(forms.Form):
    """
    Form for searching account info
    """
    RECEIVED = 'received'
    PAID = 'paid'
    TRANSACTION_TYPES = (
        (RECEIVED, _('Paid')),
        (PAID, _('Received'))
    )

    trans_type = forms.ChoiceField(
        choices=TRANSACTION_TYPES, widget=forms.RadioSelect(), required=False)
    from_date = forms.DateField(required=False, localize=True)
    to_date = forms.DateField(required=False, localize=True)

    def clean_from_date(self):
        data = self.cleaned_data['from_date']
        if data and data > datetime.date.today():
            raise forms.ValidationError(_(u'Please enter a date in the past'))
        return data

    def clean_to_date(self):
        data = self.cleaned_data['to_date']
        if data and data > datetime.date.today():
            raise forms.ValidationError(_(u'Please enter a date in the past'))
        return data

    def clean(self):
        cleaned_data = super(TransactionsSearchForm, self).clean()

        from_date = cleaned_data.get('from_date', None)
        to_date = cleaned_data.get('to_date', None)

        # If no fields completed, invalid form.
        # if not from_date and not to_date:
        #    raise forms.ValidationError(
        #        _(u'Please complete at least one search field'))

        if from_date and to_date and from_date > to_date:
            raise forms.ValidationError(
                _(u'The from date is after the to date. Please correct'))

        return cleaned_data


class TransactionsExportForm(forms.Form):
    """
    Basic copy of TransactionSearchForm, but needs to have different ids
    for the HTML to be valid, and only ever has values from
    TransactionSearchForm (without hacking). invalid form data will only
    result in failure of the export
    """
    RECEIVED = 'received'
    PAID = 'paid'
    TRANSACTION_TYPES = (
        (RECEIVED, _('Paid')),
        (PAID, _('Received'))
    )
    export_trans_type = forms.ChoiceField(
        choices=TRANSACTION_TYPES, widget=forms.RadioSelect(), required=False)
    export_from_date = forms.DateField(required=False, localize=True)
    export_to_date = forms.DateField(required=False, localize=True)


class WantCreditForm(ContactForm):
    amount = forms.DecimalField(
        label=_(u"Required amount"), max_digits=10, min_value=0.01,
        decimal_places=2,
        error_messages={'required': _(u'Please specify an amount')},
        localize=True)
    body = forms.CharField(
        widget=Textarea, label=_(u"Specify purpose"), required=True)
    earn_back = forms.CharField(
        widget=Textarea, label=_(u"Specify earn back"), required=False)

    credit_subject_template_name = "accounts/credit_email_subject.txt"
    credit_template_name = 'accounts/credit_email.txt'
    credit_enquirer_subject_template_name = \
        "accounts/credit_enquirer_email_subject.txt"
    credit_enquirer_template_name = 'accounts/credit_enquirer_email.txt'

    def credit_message(self):
        credit_template_name = self.credit_template_name
        ctx = self.get_context()
        ctx['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")
        return loader.render_to_string(credit_template_name, ctx)

    def credit_subject(self):
        ctx = self.get_context()
        ctx['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")
        credit_subject = loader.render_to_string(
            self.credit_subject_template_name, ctx)
        return ''.join(credit_subject.splitlines())

    def credit_enquirer_message(self):
        credit_enquirer_template_name = self.credit_enquirer_template_name
        ctx = self.get_context()
        ctx['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")

        return loader.render_to_string(credit_enquirer_template_name, ctx)

    def credit_enquirer_subject(self):
        ctx = self.get_context()
        ctx['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")
        credit_enquirer_subject = loader.render_to_string(
            self.credit_enquirer_subject_template_name, ctx)
        return ''.join(credit_enquirer_subject.splitlines())

    def save(self, fail_silently=False):
        # Don't use base save - no need to email site admins
        credit_message = self.credit_message()

        fb = Feedback(
            name=_("Credit Application"),
            email=settings.CREDIT_LINE_EMAIL,
            body=credit_message,
        )
        if self.request.user.is_authenticated():
            fb.user = self.request.user
        fb.save()

        credit_message_dict = {
            'from_email': self.from_email,
            'subject': self.credit_subject(),
            'recipient_list': [settings.CREDIT_LINE_EMAIL],
            'message': credit_message,
        }

        send_mail(fail_silently=fail_silently, **credit_message_dict)

        # send email to enquirer
        credit_enquirer_message_dict = {
            'from_email': self.from_email,
            'subject': self.credit_enquirer_subject(),
            'recipient_list': [self.cleaned_data['email']],
            'message': self.credit_enquirer_message(),
        }

        send_mail(fail_silently=fail_silently, **credit_enquirer_message_dict)


class ApplyFullForm(ContactForm):
    subject_template_name = "accounts/applyfull_email_subject.txt"
    template_name = 'accounts/applyfull_email.txt'
    enquirer_subject_template_name = \
        "accounts/applyfull_enquirer_email_subject.txt"
    enquirer_template_name = 'accounts/applyfull_enquirer_email.txt'

    tnc = forms.CharField(
        error_messages={
            'required': _(u'Please check this box to agree to our terms and '
                          u'conditions')},
        localize=True)

    def message(self):
        template_name = self.template_name
        ctx = self.get_context()
        ctx['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")
        return loader.render_to_string(template_name, ctx)

    def subject(self):
        ctx = self.get_context()
        ctx['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")
        subject = loader.render_to_string(self.subject_template_name,
                                          ctx)
        return ''.join(subject.splitlines())

    def enquirer_message(self):
        enquirer_template_name = self.enquirer_template_name
        ctx = self.get_context()
        ctx['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")

        return loader.render_to_string(enquirer_template_name,
                                       ctx)

    def enquirer_subject(self):
        ctx = self.get_context()
        ctx['cc3_system_name'] = getattr(
            settings, "CC3_SYSTEM_NAME", "TradeQoin")
        enquirer_subject = loader.render_to_string(
            self.enquirer_subject_template_name, ctx)
        return ''.join(enquirer_subject.splitlines())

    def save(self, fail_silently=False):
        # don't use base save - no need to email site admins
        message = self.message()

        fb = Feedback(
            name=_("Full Account Application"),
            email=settings.CREDIT_LINE_EMAIL,  # TODO: what should this be
            body=message,
        )
        if self.request.user.is_authenticated():
            fb.user = self.request.user
        fb.save()

        message_dict = {
            'from_email': self.from_email,
            'subject': self.subject(),
            'recipient_list': [settings.CREDIT_LINE_EMAIL],  # TODO: as above
            'message': message,
        }

        send_mail(fail_silently=fail_silently, **message_dict)

        # send email to enquirer
        enquirer_message_dict = {
            'from_email': self.from_email,
            'subject': self.enquirer_subject(),
            'recipient_list': [self.cleaned_data['email']],
            'message': self.enquirer_message(),
        }

        send_mail(fail_silently=fail_silently, **enquirer_message_dict)


class CloseAccountForm(forms.Form):
    close_confirmation = forms.BooleanField(
        label=_(u"I've read and accepted the terms &amp; conditions for "
                u"closing my account"),
        required=True,
        error_messages={'required': _(u'You must accept the terms & '
                                      u'conditions to close your account')})


class ConfirmCloseAccountForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.cc3_profile = self.user.cc3_profile
        self.username = self.user.username
        super(ConfirmCloseAccountForm, self).__init__(*args, **kwargs)

    def clean(self):
        # check the user has non-zero balance before continuing
        cleaned_data = super(ConfirmCloseAccountForm, self).clean()
        user_balance = self.cc3_profile.current_balance
        if user_balance < 0:
            raise forms.ValidationError(
                _(u'Your balance is negative. You cannot close your account.'))
        return cleaned_data


class ToggleImageModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        toggle_image = obj.image or settings.STATIC_URL + \
            u"images/icons/dummy_card_icon.png"
        return mark_safe("""<div class="onoffswitch-iconlabel"><img src="%s" />
                         <br />%s</div>""" % (toggle_image, str(obj)))


class AccountSecurityForm(forms.Form):
    channels = ToggleImageModelMultipleChoiceField(
        queryset=CyclosChannel.objects.all(),
        widget=ToggleSelectMultiple(
            attrs={'class': "onoffswitch-checkbox onchange-submit"}),
        required=False,
        label=_("Security Options"))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # cache the user object you pass in
        self.cc3_profile = self.user.cc3_profile
        self.username = self.user.username
        super(AccountSecurityForm, self).__init__(*args, **kwargs)

        # set all cyclos channels for initial values (not the web channel)
        self.fields['channels'].initial = [
            c.pk for c in CyclosChannel.objects.filter(is_web_channel=False)
            if not backends.check_channel(self.username, c.internal_name)
        ]
        # check the profile to see if web channel is enabled
        if not self.cc3_profile.web_payments_enabled:
            try:
                self.fields['channels'].initial.append(
                    CyclosChannel.objects.get(is_web_channel=True))
            except CyclosChannel.DoesNotExist:
                # not much can be done here - aside emailing the admin users
                # or showing a sensible error?
                pass

    def update_channels(self):
        # update cyclos channels unless marked 'is_web_channel'
        web_channel = CyclosChannel.objects.get(is_web_channel=True)
        channels = {}
        for c in CyclosChannel.objects.filter(is_web_channel=False):
            channels[c.internal_name] = not c in self.cleaned_data['channels']

        # always set web channel to be accessible:
        # (it is disabled via django front end payments being disabled)
        channels[web_channel.internal_name] = True
        backends.change_channels(self.username, channels)

        self.cc3_profile.web_payments_enabled = not (
            web_channel in self.cleaned_data['channels'])
        self.cc3_profile.save()


class ExchangeToMoneyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(ExchangeToMoneyForm, self).__init__(*args, **kwargs)

    amount = forms.DecimalField(
        label=_(u"Amount"), max_digits=10, min_value=0.01, decimal_places=2,
        error_messages={'required': _(u'Please enter an amount to convert.')},
        localize=True)

    def clean_amount(self):
        from cc3.cyclos import backends

        available_balance = backends.get_account_status(
            self.user.username).accountStatus.availableBalance

        if self.cleaned_data['amount'] > available_balance:
            raise forms.ValidationError(
                _(u'You do not have sufficient credit.'))
        return self.cleaned_data['amount']


class TimeoutForm(forms.Form):
    next = forms.CharField(max_length=255, required=True)
