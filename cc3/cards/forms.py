from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _
from .validators import card_number_validator

from .models import (Operator, Card, CARD_REGISTRATION_CHOICES,
                     CARD_REGISTRATION_CHOICES_FIRST,
                     CARD_REGISTRATION_CHOICE_OLD)

from django.core.exceptions import NON_FIELD_ERRORS
from .models import CardNumber


class OperatorForm(forms.ModelForm):
    class Meta:
        model = Operator
        # #3207 Add back the business field to benefit from the built-in
        # validate_unique() behavior from the Model
        fields = ('name', 'business', 'pin')

        # Override the default error messages for when a non-unique username is provided
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': _("The user name is already in use. Please provide a unique user name."),
            }
        }

    # #3207 Make sure that the value for the business field from the client is discarded
    def clean(self):
        cleaned_data = super(OperatorForm, self).clean()
        cleaned_data['business'] = self.initial['business']
        return cleaned_data


class CSVFileForm(forms.Form):
    csv_file = forms.FileField(label=_('CSV file'))

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']

        if not csv_file.name.lower().endswith('.csv'):
            raise forms.ValidationError(_('File uploaded must be a .csv file'))

        return csv_file


class OwnerRegisterCardForm(forms.Form):

    def __init__(self, cc3_profile, *args, **kwargs):
        self.cc3_profile = cc3_profile
        super(OwnerRegisterCardForm, self).__init__(*args, **kwargs)

        if cc3_profile.user.card_registration_set.count() == 0:
            choices = CARD_REGISTRATION_CHOICES_FIRST
        else:
            choices = CARD_REGISTRATION_CHOICES

        if not getattr(settings, 'CC3_CARDS_HANDLE_REPLACE_OLD', True):
            # remove the 'old' option from choices
            choices = [c for c in choices if c[0] !=
                       CARD_REGISTRATION_CHOICE_OLD]

        if len(choices) == 1:
            # single choice, so select it and hide the field
            self.fields['registration_choice'] = forms.CharField(
                initial=choices[0][0],
                widget=forms.HiddenInput())
        else:
            self.fields['registration_choice'] = forms.ChoiceField(
                choices=choices,
                widget=forms.RadioSelect(attrs={
                    'class': 'form-control radio'}
                ))

    def clean_registration_choice(self):
        """
        Performs an additional checking over the request user profile to see if
        it is able to order a card.
        """
        data = self.cleaned_data['registration_choice']

        if data == u'Send':
            if not self.cc3_profile.can_order_card():
                raise forms.ValidationError(
                    _('Please fill in the necessary information in your '
                      'profile for direct debit'))

        return data


class OwnerManageCardForm(forms.Form):
    """
    To be specified / implemented
    """
    pass


class BlockCardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = []


class FulfillmentProcessForm(forms.Form):
    mark_processed = forms.IntegerField(min_value=1)


class CardNumberForm(forms.ModelForm):
    class Meta:
        model = CardNumber
        fields = ['uid_number', 'number']

    number = forms.CharField(max_length=255, required=True, validators=[card_number_validator,])


