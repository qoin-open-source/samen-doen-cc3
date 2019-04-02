from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.test import TestCase
from django.utils.translation import ugettext as _

from mock import patch

from .test_factories import OperatorFactory
from cc3.cyclos.tests.test_factories import CC3ProfileFactory
from ..forms import CSVFileForm, OwnerRegisterCardForm


class CSVFileFormTestCase(TestCase):
    def test_csv_file_validation_error(self):
        """ Test ``ValidationError`` raised when file is not a .csv file """
        form = CSVFileForm()
        form.cleaned_data = {
            'csv_file': SimpleUploadedFile('bad_file_name', b'')
        }

        self.assertRaisesMessage(
            ValidationError,
            _('File uploaded must be a .csv file'),
            form.clean_csv_file)


class OwnerRegisterCardFormTestCase(TestCase):
    @patch('cc3.cyclos.models.account.CC3Profile.can_order_card')
    def test_registration_choice_validation_error(self, mock):
        """
        Tests ``ValidationError`` raised if the user is not able to get a card.
        """
        # Mock the `can_order_card()` method to always return `False`.
        mock.return_value = False

        profile = CC3ProfileFactory.create()
        form = OwnerRegisterCardForm(profile)
        form.cleaned_data = {'registration_choice': 'Send'}

        self.assertRaisesMessage(
            ValidationError,
            _('Please fill in the necessary information in your profile for '
              'direct debit'),
            form.clean_registration_choice)



