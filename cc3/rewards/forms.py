import logging

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from django.utils.translation import ugettext as _

from cc3.core.utils.files import uploaded_file_to_filename
from cc3.files.utils import (is_valid_csv_file, get_csv_max_columns,
                             get_csv_row, read_csv)

from .models import BusinessCauseSettings, UserCause
from .common import (UPLOAD_UID_EMAIL, UPLOAD_UID_CARD, UPLOAD_UID_USER_ID,
                     UPLOAD_CSV_DELIMITERS, get_bulk_upload_uid_choices)


LOG = logging.getLogger(__name__)


class BusinessCauseSettingsModelForm(forms.ModelForm):
    """
    ``BusinessCauseSettings`` model form with custom behavior. Using this
    form, the ``transaction_percentage`` field will appear disabled until the
    checkbox ``reward_by_percentage`` is clicked.
    """

    # change label to show businesses rather than username
    def __init__(self, *args, **kwargs):
        super(BusinessCauseSettingsModelForm, self).__init__(*args, **kwargs)
        self.fields['user'].label_from_instance = lambda obj: "%s (%s)" % (
            obj.cc3_profile.business_name, obj.email)

    class Meta:
        model = BusinessCauseSettings
        fields = ('user', 'transaction_percentage', 'reward_percentage')
        widgets = {
            'transaction_percentage': forms.TextInput(
                attrs={'disabled': 'true'}),
        }


UPLOAD_UID_CHOICES = {('', 'Dummy')}
UPLOAD_COLUMN_CHOICES = {('', 'Dummy')}
DONATION_PERCENT_CHOICES = {(None, _(u"Individual's chosen percentage"))}


class BulkRewardUploadFileForm(forms.Form):
    csv_file = forms.FileField(
        label=_(u"Select .CSV file to upload"),
        help_text=_(u"Make sure the CSV file is comma (,) or semicolon (;) "
                    u"separated, and values are properly quoted if "
                    u"necessary (all options in Excel)."),
    )
    has_headers = forms.BooleanField(
        label=_(u"Has header row"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': "checkbox"}),
        help_text=_(u"Tick here if the first row of the file contains "
                    u"headings, not to be treated as data")
    )

    def clean(self):
        cleaned_data = self.cleaned_data
        error_msg = ''
        try:
            csv_filename = uploaded_file_to_filename(cleaned_data['csv_file'])
        except KeyError:
            error_msg = _(u"Have you uploaded an empty file?")
        if not error_msg:
            has_headers = cleaned_data['has_headers']
            if is_valid_csv_file(filename=csv_filename,
                                 delimiters=UPLOAD_CSV_DELIMITERS):
                return cleaned_data
            error_msg = _(u"Please check that it is a valid .CSV file, "
                          u"with delimiter ',' or ';'")
        raise forms.ValidationError(
            _(u"Unable to read the .CSV file. {0}").format(error_msg))


class UserCausePercentageForm(forms.ModelForm):
    class Meta:
        model = UserCause
        fields = ('donation_percent',)

    def __init__(self, *args, **kwargs):
        self.community = kwargs.pop('community')
        super(UserCausePercentageForm, self).__init__(*args, **kwargs)

        # donation percentage is bounded by community limits
        if self.community:
            range_start = self.community.min_donation_percent
            range_stop = self.community.max_donation_percent + 1
        else:
            range_start = 0
            range_stop = 101
        # doesn't really matter sincei it's going to be hidden, but
        self.fields['donation_percent'].widget = forms.Select(
            choices=[(int(x), "{0}%".format(x)) for x in range(
                range_start, range_stop, 10)])
        self.min_percent = range_start
        self.max_percent = range_stop - 1

        if self.instance.donation_percent is None:
            # use community default as initial position
            self.initial['donation_percent'] =  \
                                    self.community.default_donation_percent

        # set an indication of width for use in template
        self.width = self.max_percent - self.min_percent


class BulkRewardUploadDetailsForm(forms.Form):
    uid_type = forms.ChoiceField(
        label=_(u"Unique user identifier type"),
        choices=UPLOAD_UID_CHOICES,
    )
    uid_column = forms.ChoiceField(
        label=_(u"Unique user identifier"),
        choices=UPLOAD_COLUMN_CHOICES,
        initial=0,
        help_text=_(
            u"Which column in the .CSV file contains the unique user "
            u"identifier? Each user must have this in his/her profile. "
            u"Blank fields are not allowed.")
    )
    amount_column = forms.ChoiceField(
        label=_(u"Amount in Positoos"),
        choices=UPLOAD_COLUMN_CHOICES,
        initial=1,
        help_text=_(
            u"Which column in the .CSV file contains the number of "
            u"Positoos to be awarded? This column must contain only "
            u"numeric values without decimals. Empty cells or values "
            u"of 0 are also not accepted.")
    )
    description_column = forms.ChoiceField(
        label=_(u"Description"),
        choices=UPLOAD_COLUMN_CHOICES,
        required=False,
        help_text=_(
            u"Which column in the .CSV file contains the  description "
            u"of the transaction? If no description is "
            u"specified in the .CSV file, users will "
            u"see the default description 'Positoos earned in shop, "
            u"business or institution' . Descriptions can not be longer "
            u"than 75 characters.")
    )
    # date column removed 3/9/15 -- see ticket #2500 -- but retained in case
    # required later
    #
    # date_column = forms.ChoiceField(
    #    label=_(u"Date, in format 'dd/mm/yyyy[ hh:mm:ss]'"),
    #    choices=UPLOAD_COLUMN_CHOICES,
    #    required=False,
    #    help_text=_(
    #        u"Which column in the .CSV file contains the date when the "
    #        u"activity took place that is being rewarded? If no date is "
    #        u"specified in the .CSV file, the upload date will be displayed "
    #        u"as the transaction date. The format for the date is "
    #        u"'dd/mm/yyyy' or optional 'dd/mm/yyyy hh:mm:ss' to give "
    #        u"an exact date for the transaction.")
    # )
    threshold_amount = forms.IntegerField(
        label=_(u'Highlight amounts above'),
        required=False,
        help_text=_(
            u"To reduce the risk of accidental large payments, you can "
            u"specify a value above which transaction is striking. When "
            u"you next click will show a pop-up window. There the number "
            u"of ratings that exceed the value specified ."),
    )
    donation_percent = forms.TypedChoiceField(
        label=_(u"Donation percentage"),
        choices=DONATION_PERCENT_CHOICES,
        required=False,
        coerce=int,
        empty_value=None,
        )

    def __init__(self, *args, **kwargs):
        """
        Dynamically generate the dropdowns based on the contents of the file
        """
        self.csv_file = kwargs.pop('csv_file')
        self.has_headers = kwargs.pop('has_headers')
        self.community = kwargs.pop('community')
        self.can_vary_percent = kwargs.pop('can_vary_percent')

        super(BulkRewardUploadDetailsForm, self).__init__(*args, **kwargs)

        self.csv_filename = uploaded_file_to_filename(self.csv_file)
        if self.has_headers:
            headers = get_csv_row(self.csv_filename,
                                  delimiters=UPLOAD_CSV_DELIMITERS)
        else:
            num_cols = get_csv_max_columns(self.csv_filename,
                                           delimiters=UPLOAD_CSV_DELIMITERS)
            headers = [_(u"Column") + " {0}".format(chr(65+i))
                       for i in range(num_cols)]

        upload_choices = [(i, header) for i, header in enumerate(headers)]
        self.fields['uid_column'].choices = upload_choices
        self.fields['amount_column'].choices = upload_choices
        self.fields['description_column'].choices = [
            ('', '---------')
        ] + upload_choices

        # self.fields['date_column'].choices = [('','---------')] +
        #     upload_choices

        self.fields['uid_type'].choices = get_bulk_upload_uid_choices()

        # hide donation_ercent if not allowed to change
        if not self.can_vary_percent:
            self.fields['donation_percent'].widget = forms.HiddenInput()
        else:
            # donation percentage is NOT bounded by community limits
            range_start = 0
            range_stop = 101
            self.fields['donation_percent'].choices = [
                (None, _(u"Individual's chosen percentage"))
            ] + [(int(x), "{0}%".format(x)) for x in range(
                range_start, range_stop, 10)]


    def clean(self):
        # check that the column selections are distinct
        cleaned_data = self.cleaned_data
        self.uid_type = cleaned_data['uid_type']
        self.uid_column = int(cleaned_data['uid_column'])
        self.amount_column = int(cleaned_data['amount_column'])
        try:
            self.description_column = int(
                cleaned_data.get('description_column'))
        except (KeyError, TypeError, ValueError):
            self.description_column = None
        # try:
        #    self.date_column = int(cleaned_data.get('date_column'))
        # except (KeyError, TypeError, ValueError):
        #    self.date_column = None
        column_list = [
            self.uid_column, self.amount_column,
            self.description_column,  # self.date_column,
        ]
        non_null_cols = [c for c in column_list if c is not None]
        distinct_cols = set(non_null_cols)
        if len(distinct_cols) < len(non_null_cols):
            raise forms.ValidationError(_(
                u"Column selections must be distinct"))

        # now read the whole file, and build a list of validation errors
        errors = self.validate_rewards_csv()

        if errors:
            raise forms.ValidationError(errors)

        cleaned_data.update({
            'uid_column': self.uid_column,
            'amount_column': self.amount_column,
            'description_column': self.description_column,
            # 'date_column': self.date_column,
        })

        return cleaned_data

    def validate_rewards_csv(self):
        """
        Validate the csv file by reading through and checking:
        - amount column contains positive integers
        - date column (if supplied) contains correctly formatted date(time)
        - description column (if supplied) contains up to 75 chars
        - unique uid column is correctly formatted for chosen type
          (email address, QW user id)
        Return a list of errors
        """
        message_common = _(u"Please check the .csv file and ensure "
                           u"that you have selected the right columns."
                           u"\n\nAffects row number(s):\n")
        missing_columns = []
        invalid_amounts = []
        invalid_uids = []
        # invalid_dates = []
        invalid_descriptions = []
        if self.has_headers:
            skip_rows = 1
            row_number_adjust = 2
        else:
            row_number_adjust = 1
            skip_rows = 0
        for i, row in enumerate(read_csv(self.csv_filename,
                                         delimiters=UPLOAD_CSV_DELIMITERS,
                                         skip_rows=skip_rows)):
            data = {}
            try:
                data = {
                    'uid': row[self.uid_column],
                    'amount': row[self.amount_column],
                    'description': '',
                    # 'date': ''
                }
                if self.description_column is not None:
                    data['description'] = row[self.description_column]
                # if self.date_column is not None:
                #    data['date'] = row[self.date_column]
            except IndexError:
                missing_columns.append(i)
                next

            # LOG.info(data)

            validation_form = self.get_validation_form(data)
            if not validation_form.is_valid():
                if validation_form.errors.has_key('amount'):
                    invalid_amounts.append(i)
                if validation_form.errors.has_key('description'):
                    invalid_descriptions.append(i)
                # if validation_form.errors.has_key('date'):
                #    invalid_dates.append(i)
                if validation_form.errors.has_key('uid'):
                    invalid_uids.append(i)

        errors = []
        if invalid_uids:
            affected_rows = ', '.join(
                [str(i+row_number_adjust) for i in invalid_uids])
            errors.append(self.get_uid_error_snippet() +
                          message_common + affected_rows)
        if invalid_amounts:
            affected_rows = ', '.join(
                [str(i+row_number_adjust) for i in invalid_amounts])
            errors.append(_(u"Some of the values in the 'Amount in Positoos' "
                            u"column are not positive integers. ") +
                          message_common + affected_rows)
        # if invalid_dates:
        #    affected_rows = ', '.join([
        #        str(i+row_number_adjust) for i in invalid_dates])
        #    errors.append(_(u"Some of the values in the 'Date' column are not "
        #                    u"in the correct format (dd/mm/yyyy hh:mm:ss). ") +
        #                  message_common + affected_rows)
        if invalid_descriptions:
            affected_rows = ', '.join(
                [str(i+row_number_adjust) for i in invalid_descriptions])
            errors.append(_(u"Some of the values in the 'Description' column "
                            u"exceed the maximum of 75 characters. ") +
                          message_common + affected_rows)
        if missing_columns:
            affected_rows = ', '.join([
                str(i+row_number_adjust) for i in missing_columns])
            errors.append(_(u"Some rows do not have enough columns. ") +
                          message_common + affected_rows)
        return errors

    def get_validation_form(self, data):
        """Returns the correct validation form for the chosen UID type"""
        if self.uid_type == UPLOAD_UID_EMAIL:
            return UploadDataValidationFormWithEmail(data)
        if self.uid_type == UPLOAD_UID_CARD:
            return UploadDataValidationFormWithCard(data)
        if self.uid_type == UPLOAD_UID_USER_ID:
            return UploadDataValidationFormWithUserID(data)
        return UploadBaseDataValidationForm(data)

    def get_uid_error_snippet(self):
        """Returns the correct error message for the chosen UID type"""
        if self.uid_type == UPLOAD_UID_EMAIL:
            return _(u"Some of the values in the 'Email' column are "
                     u"not in the correct format. ")
        if self.uid_type == UPLOAD_UID_CARD:
            return _(u"Some of the values in the 'Card number' column "
                     u"are not in the correct format. ")
        if self.uid_type == UPLOAD_UID_USER_ID:
            return _(u"Some of the values in the 'Qoinware User ID' column "
                     u"are not numeric. ")


class BulkRewardUploadConfirmationForm(forms.Form):
    # dummy form, for confirmation screen
    def __init__(self, *args, **kwargs):
        """
        Pop all the kwargs for later use
        """
        self.csv_file = kwargs.pop('csv_file')
        self.has_headers = kwargs.pop('has_headers')
        self.uid_type = kwargs.pop('uid_type')
        self.uid_column = kwargs.pop('uid_column')
        self.amount_column = kwargs.pop('amount_column')
        self.description_column = kwargs.pop('description_column')
        # self.date_column = kwargs.pop('date_column')
        self.threshold_amount = kwargs.pop('threshold_amount')
        self.can_vary_percent = kwargs.pop('can_vary_percent')
        self.donation_percent = kwargs.pop('donation_percent')
        self.community = kwargs.pop('community')

        super(BulkRewardUploadConfirmationForm, self).__init__(*args, **kwargs)


# forms used to validate the csv data
class UploadBaseDataValidationForm(forms.Form):
    # date_formats = ['%d/%m/%Y',
    #                '%d/%m/%Y %H:%M',
    #                '%d/%m/%Y %H:%M:%S']

    amount = forms.IntegerField(validators=[MinValueValidator(1), ])
    description = forms.CharField(max_length=75, required=False)
    # date = forms.DateTimeField(input_formats=date_formats, required=False)


class UploadDataValidationFormWithEmail(UploadBaseDataValidationForm):
    uid = forms.EmailField()


class UploadDataValidationFormWithCard(UploadBaseDataValidationForm):
    uid = forms.IntegerField(validators=[
        MaxValueValidator(99999), MinValueValidator(0)])


class UploadDataValidationFormWithUserID(UploadBaseDataValidationForm):
    uid = forms.IntegerField(validators=[
        MinValueValidator(0)])
