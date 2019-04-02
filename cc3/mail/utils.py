import logging

from django.utils.translation import ugettext_lazy as _

from .models import MailMessage

LOG = logging.getLogger('cc3.mail.utils')


def send_mail_to(recipients, mail_type, language, context=None,
                 recipient_addresses=()):
    """Send (separate copy of) email to all recipients

    recipients is a list of CC3Profiles
    recipient_addresses is an optional additional list of email addresses
    Returns number of emails successfully sent
    """
    num_sent = 0
    try:
        msg = MailMessage.objects.get_msg(mail_type, lang=language)
    except MailMessage.DoesNotExist as e:
        LOG.error('Failed to send {0} email: {1}'.format(mail_type, e))
        return num_sent

    for recipient in recipients:
        try:
            msg.send(recipient.user.email, context)
            num_sent += 1
        except Exception as e:
            LOG.error('Failed to send {0} email to {2}: {1}'.format(
                                                mail_type, e, recipient))
    for mailaddress in recipient_addresses:
        try:
            msg.send(mailaddress, context)
            num_sent += 1
        except Exception as e:
            LOG.error('Failed to send {0} email to {2}: {1}'.format(
                                                mail_type, e, mailaddress))

    return num_sent