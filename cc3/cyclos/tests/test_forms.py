from unittest.case import skip

from django.conf import settings
from django.forms import ValidationError
from django.test import TestCase
from django.test.utils import override_settings

from django.utils.translation import activate, ugettext_lazy as _

from cc3.core.tests.test_factories import CategoryFactory
from cc3.cyclos.tests.test_factories import CC3CommunityFactory
from ..forms import CC3ProfileForm


class CC3ProfileFormTestCase(TestCase):
    def setUp(self):
        community = CC3CommunityFactory.create()
        category = CategoryFactory.create()

        self.form = CC3ProfileForm()

        self.form.cleaned_data = {
            'community': community.pk,
            'first_name': 'John',
            'last_name': 'Doe',
            'business_name': 'Maykin Media',
            'job_title': 'Developer',
            'country': 'NL',
            'city': 'Amsterdam',
            'address': 'Herengracht 416',
            'postal_code': '1017BZ',
            'phone_number': '+31 (0)207530523',
            'mobile_number': '+31 616844084',
            'company_website': 'http://www.maykinmedia.nl',
            'company_description': 'We provide hassle-free, custom-made '
                                   'websites and webapps for clients.',
            'is_visible': True,
            'categories': [category]
        }

        activate('en')

    def tearDown(self):
        activate(settings.LANGUAGE_CODE)

    def test_clean_first_name(self):
        """
        Tests ``ValidationError`` raised when no ``first_name`` is provided.
        """
        del self.form.cleaned_data['first_name']

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter your First Name'),
            self.form.clean_first_name)

    @override_settings(PROFILE_FORMS_MAX_LENGTH_FIRST_NAME=10)
    def test_clean_first_name_too_long(self):
        """
        Tests ``ValidationError`` raised when ``first_name`` is too long
        """
        self.form.cleaned_data['first_name'] = 'toolongname'

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a First name of 10 or fewer characters'),
            self.form.clean_first_name)

    def test_clean_first_name_length_ignored_by_default(self):
        """
        Tests no ``ValidationError`` raised for length if no limit set
        """
        self.form.cleaned_data['first_name'] = 'toolongname'*20

        try:
            self.form.clean()
        except:
            self.fail("Shouldn't raise an exception")

    def test_clean_last_name(self):
        """
        Tests ``ValidationError`` raised when no ``last_name`` is provided.
        """
        del self.form.cleaned_data['last_name']

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter your Last Name'),
            self.form.clean_last_name)

    @override_settings(PROFILE_FORMS_MAX_LENGTH_LAST_NAME=10)
    def test_clean_last_name_too_long(self):
        """
        Tests ``ValidationError`` raised when ``last_name`` is too long
        """
        self.form.cleaned_data['last_name'] = 'toolongname'

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a Last name of 10 or fewer characters'),
            self.form.clean_last_name)

    def test_clean_business_name(self):
        """
        Tests ``ValidationError`` raised when no ``business_name`` is provided.
        """
        del self.form.cleaned_data['business_name']

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter your Business Name'),
            self.form.clean_business_name)

    @override_settings(PROFILE_FORMS_MAX_LENGTH_BUSINESS_NAME=10)
    def test_clean_first_name_too_long(self):
        """
        Tests ``ValidationError`` raised when ``business_name`` is too long
        """
        self.form.cleaned_data['business_name'] = 'toolongname'

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a Business name of 10 or fewer characters'),
            self.form.clean_business_name)

    def test_clean_address(self):
        """
        Tests ``ValidationError`` raised when no ``address`` is provided.
        """
        del self.form.cleaned_data['address']

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter your Address'),
            self.form.clean_address)

    def test_clean_phone_number(self):
        """
        Tests ``ValidationError`` raised when a wrong ``phone_number`` is
        provided.
        """
        self.form.cleaned_data['phone_number'] = 'ABCDE'

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a valid Phone Number'),
            self.form.clean_phone_number)

    @override_settings(CUSTOM_PHONE_REGEX=r'^02[0-9]{8}$')
    def test_clean_phone_number_custom(self):
        """
        Tests ``ValidationError`` raised when ``phone_number``
        doesn't fit custom regex.
        """
        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a valid Phone Number'),
            self.form.clean_phone_number)

    @override_settings(CUSTOM_PHONE_REGEX=r'^02[0-9]{8}$')
    def test_clean_phone_number_spaces(self):
        """
        Tests spaces are silently removed from ``phone_number``
        """
        self.form.cleaned_data['phone_number'] = '0 2 1 2 3 4 5 6 7 8'
        self.assertEqual(self.form.clean_phone_number(), '0212345678')

    @override_settings(CUSTOM_PHONE_REGEX=r'^02[0-9]{8}$')
    @override_settings(CUSTOM_PHONE_REGEX_DESC="Should start with '02'")
    def test_clean_phone_number_custom_description(self):
        """
        Tests ``ValidationError`` raised when ``phone_number``
        doesn't fit custom regex.
        """
        self.assertRaisesMessage(
            ValidationError,
            _("Please enter a valid Phone Number (Should start with '02')"),
            self.form.clean_phone_number)

    @override_settings(MOBILE_NUMBER_MANDATORY=True)
    def test_clean_mobile_number_empty(self):
        """
        Tests ``ValidationError`` raised when no ``mobile_number`` is provided.
        """
        del self.form.cleaned_data['mobile_number']

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter your Mobile Number'),
            self.form.clean_mobile_number)

    @override_settings(MOBILE_NUMBER_MIN_LENGTH=8, MOBILE_NUMBER_MANDATORY=True)
    def test_clean_mobile_number_minimum_digits(self):
        """
        Tests ``ValidationError`` raised when a ``mobile_number`` with less
        digits than defined in ``MOBILE_NUMBER_MIN_LENGTH`` is provided.
        """
        self.form.cleaned_data['mobile_number'] = '+31 616'

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a mobile number of at least 8 digits'),
            self.form.clean_mobile_number)

    @override_settings(MOBILE_NUMBER_MAX_LENGTH=8, MOBILE_NUMBER_MANDATORY=True)
    def test_clean_mobile_number_maximum_digits(self):
        """
        Tests ``ValidationError`` raised when a ``mobile_number`` with more
        digits than defined in ``MOBILE_NUMBER_MIN_LENGTH`` is provided.
        """
        self.form.cleaned_data['mobile_number'] = '+31 616844084'

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a mobile number of at most 8 digits'),
            self.form.clean_mobile_number)

    def test_clean_mobile_number_invalid(self):
        """
        Tests ``ValidationError`` raised when a wrong ``mobile_number`` is
        provided.
        """
        self.form.cleaned_data['mobile_number'] = 'ABCDE'

        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a valid Mobile Number'),
            self.form.clean_mobile_number)

    @override_settings(CUSTOM_MOBILE_REGEX=r'^06[0-9]{8}$')
    def test_clean_mobile_number_custom(self):
        """
        Tests ``ValidationError`` raised when ``mobile_number``
        doesn't fit custom regex.
        """
        self.assertRaisesMessage(
            ValidationError,
            _('Please enter a valid Mobile Number'),
            self.form.clean_mobile_number)

    @override_settings(CUSTOM_MOBILE_REGEX=r'^06[0-9]{8}$')
    def test_clean_mobile_number_spaces(self):
        """
        Tests spaces are silently removed from ``mobile_number``
        """
        self.form.cleaned_data['mobile_number'] = '0 6    1 2 3 4 5 6 7 8'
        self.assertEqual(self.form.clean_mobile_number(), '0612345678')

    @override_settings(CUSTOM_MOBILE_REGEX=r'^06[0-9]{8}$')
    @override_settings(CUSTOM_MOBILE_REGEX_DESC="Should start with '06'")
    def test_clean_mobile_number_custom_description(self):
        """
        Tests ``ValidationError`` raised when ``mobile_number``
        doesn't fit custom regex.
        """
        self.assertRaisesMessage(
            ValidationError,
            _("Please enter a valid Mobile Number (Should start with '06')"),
            self.form.clean_mobile_number)

    @skip("Obsolete, registration_form removed from core")
    @override_settings(KVK_NUMBER_IN_PROFILE=True)
    def test_clean_registration_number(self):
        """
        Tests valid ``registration_number`` OK
        """
        self.form.cleaned_data['registration_number'] = '12345678'

        try:
            self.form.clean()
        except:
            self.fail("Shouldn't raise an exception")

    @skip("Obsolete, registration_form removed from core")
    @override_settings(KVK_NUMBER_IN_PROFILE=True)
    def test_clean_registration_number_too_short(self):
        """
        Tests ``ValidationError`` raised when ``registration_number`` is < 8
        digits
        """
        self.form.cleaned_data['registration_number'] = '1234567'

        self.assertRaisesMessage(
            ValidationError,
            _('KvK number should be 8 digits'),
            self.form.clean_registration_number)

    @skip("Obsolete, registration_form removed from core")
    @override_settings(KVK_NUMBER_IN_PROFILE=True)
    def test_clean_registration_number_too_long(self):
        """
        Tests ``ValidationError`` raised when ``registration_number`` is > 8
        digits
        """
        self.form.cleaned_data['registration_number'] = '123456789'

        self.assertRaisesMessage(
            ValidationError,
            _('KvK number should be 8 digits'),
            self.form.clean_registration_number)

    @skip("Obsolete, registration_form removed from core")
    @override_settings(KVK_NUMBER_IN_PROFILE=True)
    def test_clean_registration_number_not_digits(self):
        """
        Tests ``ValidationError`` raised when ``registration_number`` is not
        digits
        """
        self.form.cleaned_data['registration_number'] = '1234567x'

        self.assertRaisesMessage(
            ValidationError,
            _('KvK number should be 8 digits'),
            self.form.clean_registration_number)

    @skip("Obsolete, registration_form removed from core")
    @override_settings(KVK_NUMBER_IN_PROFILE=False)
    def test_clean_registration_number_ignored_if_not_configured(self):
        """
        Tests invalid ``registration_number`` ignored if not
        KVK_NUMBER_IN_PROFILE not True
        """
        self.form.cleaned_data['registration_number'] = 'blah'

        try:
            self.form.clean()
        except:
            self.fail("Shouldn't raise an exception")

    def test_clean_empty_names(self):
        """
        Tests ``ValidationError`` raised when no names at all are provided.
        """
        del self.form.cleaned_data['first_name']
        del self.form.cleaned_data['last_name']
        del self.form.cleaned_data['business_name']

        self.assertRaisesMessage(
            ValidationError,
            _('Please check the form for errors'),
            self.form.clean)
