from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import SortedDict
from django.utils.formats import date_format, time_format
from django.utils.translation import ugettext as _

from cc3.excelexport.views import ExcelResponse


def card_fulfillment_excel_response(export_card_fulfilment_list):
    if len(export_card_fulfilment_list) == 0:
        export_card_fulfilment_list_p = [export_card_fulfilment_list]
    else:
        # massage the data
        export_card_fulfilment_list_p, headings = process_card_fulfillment_list(export_card_fulfilment_list)

    return ExcelResponse(export_card_fulfilment_list_p, force_csv=True, header_override=headings,
                         output_name="card_fulfillment")


def process_card_fulfillment_list(card_fulfillment_list):
    """
    Helper function to export card fulfillments to a text file.
    NB Will only work with Samen Doen cards due to Profile class arrangements.
    Hooks available to move this out of CC3 core to Samen Doen
    """
    processed_card_fulfillments = []

    for fulfillment in card_fulfillment_list:
        try:
            user_profile = fulfillment.profile.user.get_profile()
        except ObjectDoesNotExist:
            # Can do better when this fn is moved out of CC3 core, but for now:
            # get_profile() does work in User is inactive, so use the CC3Profile
            # and use dummy values where not available
            user_profile = fulfillment.profile
            user_profile.num_street = '-'
            user_profile.extra_address = '-'
            user_profile.is_stadlander_sso_user = None
            user_profile.individual_profile = None
        trans_dict = SortedDict()
        trans_dict['name'] = user_profile.name
        trans_dict['address'] = user_profile.address
        trans_dict['num_street'] = user_profile.num_street
        trans_dict['extra_address'] = user_profile.extra_address
        trans_dict['postal_code'] = user_profile.postal_code
        trans_dict['city'] = user_profile.city
        trans_dict['email'] = user_profile.user.email
        if user_profile.is_stadlander_sso_user is not None:
            trans_dict['is_stadlander_sso_user'] = user_profile.is_stadlander_sso_user()
        else:
            trans_dict['is_stadlander_sso_user'] = '-'
        if user_profile.individual_profile is not None:
            trans_dict['iban'] = user_profile.individual_profile.iban
            trans_dict['bic_code'] = user_profile.individual_profile.bic_code
            trans_dict['account_holder'] = user_profile.individual_profile.account_holder
        else:
            trans_dict['iban'] = '-'
            trans_dict['bic_code'] = '-'
            trans_dict['account_holder'] = '-'
        trans_dict['creation_date'] = u"{0} {1}".format(
            date_format(fulfillment.card_registration.creation_date, use_l10n=True),
            time_format(fulfillment.card_registration.creation_date, use_l10n=True))
        trans_dict['registration_choice'] = fulfillment.card_registration.registration_choice
        trans_dict['status'] = fulfillment.status

        processed_card_fulfillments.append(trans_dict)

    headings = [_('Name'), _('Address'), _('Num Street'), _('Extra Address'), _('Postal Code'), _('City'), _('Email'),
                _('Stadlander'), _('IBAN'), _('BIC Code'), _('Account Holder'), _('Creation Date'), _('Send / Old'),
                _('Status')]
    return processed_card_fulfillments, headings
