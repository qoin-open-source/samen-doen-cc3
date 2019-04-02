from django.core.validators import RegexValidator
from django.utils.translation import ugettext as _
from django.conf import settings

max_card_num = getattr(settings, 'MAX_CARD_NUMBER', 9999999999999999)
min_card_num = getattr(settings, 'MIN_CARD_NUMBER', 0)

iccid_validator = RegexValidator(
    regex=r"^\d{19,20}$", message=_('Enter a valid ICCID (19 or 20 digits)'),
    code='invalid_iccid')

operator_pin_validator = RegexValidator(
    regex=r"^\d{4}$", message=_("PIN must be 4 digits"),
    code='invalid_operator_pin')

card_number_validator = RegexValidator(
    regex=r"^\d{1,16}$", message=_("Enter a valid card number (up to 16 digits)"),
    code='invalid_card_number')

imei_number_validator = RegexValidator(
    regex=r"^\d{15}$", message=_("Enter a valid IMEI number (15 digits)"),
    code='invalid_imei_number')


