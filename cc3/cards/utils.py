import logging
import importlib

from django.conf import settings

from cc3.mail.models import MailMessage

from .excel import card_fulfillment_excel_response

LOG = logging.getLogger('cc3.card.utils')


def mail_card_admins(instance, mail_type, language):
    """
    Send CARD_ADMINISTRATOR_EMAILS an email using the cc3.mail MailMessage
    wrapper.
    """
    card_admin_emails = getattr(settings, 'CARD_ADMINISTRATOR_EMAILS', [])
    try:
        msg = MailMessage.objects.get_msg(mail_type, lang=language)
    except MailMessage.DoesNotExist as e:
        LOG.warning('Not sending new user notifications: {0}'.format(e))
        return

    for card_admin_email in card_admin_emails:
        try:
            msg.send(card_admin_email, {'user_profile': instance})
        except Exception as e:
            # Widely catch every exception to avoid blocking the registration
            # process. Log it for maintenance.
            LOG.error('Not sending email to card admin {0}: '
                      '{1}'.format(card_admin_email, e))


def generate_card_fulfillment_excel(export_card_fulfilment_list):
    """
    Generate card fulfillment. Allow Child project to provide the
    ExcelResponse via setting.
    """
    card_fulfillment_excel_module = getattr(
        settings, 'CARD_FULFILLMENT_EXCEL_MODULE', None)

    if not card_fulfillment_excel_module:
        return card_fulfillment_excel_response(export_card_fulfilment_list)
    else:
        card_fulfillment_excel_module = importlib.import_module(
            card_fulfillment_excel_module)
        return card_fulfillment_excel_module.card_fulfillment_excel_response(
            export_card_fulfilment_list)
