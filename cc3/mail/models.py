from email.mime.base import MIMEBase
import re
import os
from cc3.core.utils import UploadTo

from django.db import models
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, SafeMIMEMultipart
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.template import Context, Template

MAIL_TYPE_NEW_REGISTRATION_USER = 'newreguser'
MAIL_TYPE_PASSWORD_RESET = 'passwordreset'
MAIL_TYPE_NEW_REGISTRATION = 'newreg'
MAIL_TYPE_NEW_STADLANDER_REGISTRATION = 'newregstadlander'
MAIL_TYPE_PROFILE_COMPLETED = 'profilecompleted'
MAIL_TYPE_NEW_PAYMENT = 'newtransaction'
MAIL_TYPE_AD_ONHOLD = 'adonhold'
MAIL_TYPE_ENQUIRY_ENQUIRER = 'enquiryenquirer'
MAIL_TYPE_ENQUIRY_ADVERTISER = 'enquiryadvertiser'
MAIL_TYPE_ENQUIRY_ADMINS = 'enquiryadmins'
MAIL_TYPE_MATCHING_CATEGORIES = 'matchingcats'
MAIL_TYPE_UPDATED_CATEGORIES = 'updatedcats'
MAIL_TYPE_EXCHANGE_TO_MONEY = 'exchangetomoney'
# balance warning emails
MAIL_TYPE_NEGATIVE_BALANCE_USER = 'negbalanceuser'
MAIL_TYPE_NEGATIVE_BALANCE_ADMINS = 'negbalanceadmins'
MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_USER = 'negbalancecollectuser'
MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_ADMINS = 'negbalancecollectadmins'
MAIL_TYPE_LARGE_BALANCE_USER = 'largebalanceuser'
MAIL_TYPE_LARGE_BALANCE_ADMINS = 'largebalanceadmins'
# card registration emails
MAIL_TYPE_SEND_USER_CARD = 'usercard'
MAIL_TYPE_USER_HAS_NEW_CARD = 'newcard'
MAIL_TYPE_USER_HAS_OLD_CARD = 'oldcard'
MAIL_TYPE_USER_SHOP_CARD = 'shopcard'
# prizedraw emails
MAIL_TYPE_BULK_TICKET_PURCHASE = 'bulkpurchase'
MAIL_TYPE_PRIZEDRAW_NEW_REGISTRATION = 'prizedrawnewreg'
# invoices
MAIL_TYPE_MONTHLY_INVOICE = 'monthlyinvoice'
# camapaigns (aka activities)
MAIL_TYPE_CAMPAIGN_SIGNUP_CONFIRM = 'campaignsignup'
MAIL_TYPE_CAMPAIGN_SIGNUP_NOTIFY = 'campaignsignupowner'
MAIL_TYPE_CAMPAIGN_UPDATED = 'campaignupdated'
MAIL_TYPE_CAMPAIGN_CANCELLED = 'campaigncancelled'
MAIL_TYPE_CAMPAIGN_UNSUBSCRIBED = 'campaignunsubscribed'
MAIL_TYPE_CAMPAIGN_CREATED = 'campaigncreated'


MAIL_MESSAGE_CHOICES = (
    (MAIL_TYPE_PASSWORD_RESET, 'Password reset email'),
    (MAIL_TYPE_NEW_REGISTRATION_USER, 'New registration email for user'),
    (MAIL_TYPE_NEW_REGISTRATION, 'New registration email'),
    (MAIL_TYPE_NEW_STADLANDER_REGISTRATION,
     'New (Stadlander) registration email (to user)'),
    (MAIL_TYPE_PROFILE_COMPLETED, 'Profile completed email'),
    (MAIL_TYPE_NEW_PAYMENT, 'Transaction completed email'),
    (MAIL_TYPE_AD_ONHOLD, 'New or updated Ad needs approval'),
    (MAIL_TYPE_SEND_USER_CARD, 'Send user card'),
    (MAIL_TYPE_ENQUIRY_ENQUIRER, 'Ad enquiry email for enquirer'),
    (MAIL_TYPE_ENQUIRY_ADVERTISER, 'Ad enquiry email for advertiser'),
    (MAIL_TYPE_ENQUIRY_ADMINS, 'Ad enquiry email for admins'),
    (MAIL_TYPE_NEGATIVE_BALANCE_USER, 'Negative balance warning email'),
    (MAIL_TYPE_NEGATIVE_BALANCE_ADMINS, 'Negative balance email for admins'),
    (MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_USER,
     'Negative balance collection email'),
    (MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_ADMINS,
     'Negative balance collection email for admins'),
    (MAIL_TYPE_LARGE_BALANCE_USER, 'Large balance warning email'),
    (MAIL_TYPE_LARGE_BALANCE_ADMINS, 'Large balance email for admins'),
    (MAIL_TYPE_MATCHING_CATEGORIES, 'Daily Matching Wants/Offers email'),
    (MAIL_TYPE_UPDATED_CATEGORIES, 'Profile Updated Wants/Offers email'),
    (MAIL_TYPE_EXCHANGE_TO_MONEY, 'Exchange to Money performed'),
    (MAIL_TYPE_BULK_TICKET_PURCHASE, 'Bulk prizedraw tickets purchased'),
    (MAIL_TYPE_PRIZEDRAW_NEW_REGISTRATION, 'Prizedraw new registration email'),
    (MAIL_TYPE_MONTHLY_INVOICE, 'Notification of monthly invoice'),
    (MAIL_TYPE_CAMPAIGN_SIGNUP_CONFIRM,
     'Campaigns: Confirmation on signing up'),
    (MAIL_TYPE_CAMPAIGN_SIGNUP_NOTIFY,
     'Campaigns: Notify owner of new signup'),
    (MAIL_TYPE_CAMPAIGN_UPDATED,
     'Campaigns: Notify participants a campaign has been edited'),
    (MAIL_TYPE_CAMPAIGN_CANCELLED,
     'Campaigns: Notify participants a campaign has been cancelled'),
    (MAIL_TYPE_CAMPAIGN_UNSUBSCRIBED,
     'Campaigns: Notify participant they have been removed'),
    (MAIL_TYPE_CAMPAIGN_CREATED,
     'Campaigns: Notify members of new campaign (optional)'),
)

MAIL_MESSAGE_REQUIRED_FIELDS = {
    MAIL_TYPE_PASSWORD_RESET: ['first_name', 'last_name', 'link'],
    MAIL_TYPE_NEW_REGISTRATION_USER: ['link'],
    MAIL_TYPE_NEW_REGISTRATION: ['user_profile'],
    MAIL_TYPE_NEW_STADLANDER_REGISTRATION: ['user_profile'],
    MAIL_TYPE_PROFILE_COMPLETED: ['user_profile'],
    MAIL_TYPE_NEW_PAYMENT: ['payment', 'sender', 'receiver'],
    MAIL_TYPE_SEND_USER_CARD: ['user_profile', ],
    MAIL_TYPE_AD_ONHOLD: ['ad_url', ],
    MAIL_TYPE_ENQUIRY_ENQUIRER: [],
    MAIL_TYPE_ENQUIRY_ADVERTISER: [],
    MAIL_TYPE_ENQUIRY_ADMINS: [],
    MAIL_TYPE_NEGATIVE_BALANCE_USER: [],
    MAIL_TYPE_NEGATIVE_BALANCE_ADMINS: [],
    MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_USER: [],
    MAIL_TYPE_NEGATIVE_BALANCE_COLLECT_ADMINS: [],
    MAIL_TYPE_LARGE_BALANCE_USER: [],
    MAIL_TYPE_LARGE_BALANCE_ADMINS: [],
    MAIL_TYPE_MATCHING_CATEGORIES: [],
    MAIL_TYPE_UPDATED_CATEGORIES: [],
    MAIL_TYPE_EXCHANGE_TO_MONEY: [],
    MAIL_TYPE_BULK_TICKET_PURCHASE: ['tickets_purchased'],
    MAIL_TYPE_PRIZEDRAW_NEW_REGISTRATION: ['username', 'password'],
    MAIL_TYPE_MONTHLY_INVOICE: [],
    MAIL_TYPE_CAMPAIGN_SIGNUP_CONFIRM: [],
    MAIL_TYPE_CAMPAIGN_SIGNUP_NOTIFY: [],
    MAIL_TYPE_CAMPAIGN_UPDATED: [],
    MAIL_TYPE_CAMPAIGN_CANCELLED: [],
    MAIL_TYPE_CAMPAIGN_UNSUBSCRIBED: [],
    MAIL_TYPE_CAMPAIGN_CREATED: [],
}

# Define {{ body|linebreaks }} to place the content
# Set to None if only plain-text emails are to be sent
MAIL_HTML_TEMPLATE = None


class EmailMultiRelated(EmailMultiAlternatives):
    """
    A version of EmailMessage that makes it easy to send multipart/related
    messages. For example, including text and HTML versions with inline images.

    @see https://djangosnippets.org/snippets/2215/
    @see https://djangosnippets.org/snippets/3001/
    """
    related_subtype = 'related'

    def __init__(self, *args, **kwargs):
        # self.related_ids = []
        self.related_attachments = []
        super(EmailMultiRelated, self).__init__(*args, **kwargs)

    def attach_related(self, filename=None, content=None, mimetype=None):
        """
        Attaches a file with the given filename and content. The filename can
        be omitted and the mimetype is guessed, if not provided.

        If the first parameter is a MIMEBase subclass it is inserted directly
        into the resulting message attachments.
        """
        if isinstance(filename, MIMEBase):
            assert content == mimetype == None
            self.related_attachments.append(filename)
        else:
            assert content is not None
            self.related_attachments.append((filename, content, mimetype))

    def attach_related_file(self, path, mimetype=None):
        """Attaches a file from the filesystem."""
        filename = os.path.basename(path)
        content = open(path, 'rb').read()
        self.attach_related(filename, content, mimetype)

    def _create_message(self, msg):
        return self._create_attachments(self._create_related_attachments(
            self._create_alternatives(msg)))

    def _create_alternatives(self, msg):
        for i, (content, mimetype) in enumerate(self.alternatives):
            if mimetype == 'text/html':
                for related_attachment in self.related_attachments:
                    if isinstance(related_attachment, MIMEBase):
                        content_id = related_attachment.get('Content-ID')
                        content = re.sub(
                            r'(?<!cid:)%s' % re.escape(content_id),
                            'cid:%s' % content_id, content)
                    else:
                        filename, _, _ = related_attachment
                        content = re.sub(
                            r'(?<!cid:)%s' % re.escape(filename),
                            'cid:%s' % filename, content)
                self.alternatives[i] = (content, mimetype)

        return super(EmailMultiRelated, self)._create_alternatives(msg)

    def _create_related_attachments(self, msg):
        encoding = self.encoding or settings.DEFAULT_CHARSET
        if self.related_attachments:
            body_msg = msg
            msg = SafeMIMEMultipart(_subtype=self.related_subtype,
                                    encoding=encoding)
            if self.body:
                msg.attach(body_msg)
            for related_attachment in self.related_attachments:
                if isinstance(related_attachment, MIMEBase):
                    msg.attach(related_attachment)
                else:
                    msg.attach(self._create_related_attachment(
                        *related_attachment))
        return msg

    def _create_related_attachment(self, filename, content, mimetype=None):
        """
        Convert the filename, content, mimetype triple into a MIME attachment
        object. Adjust headers to use Content-ID where applicable.
        Taken from http://code.djangoproject.com/ticket/4771
        """
        attachment = super(EmailMultiRelated, self)._create_attachment(
            filename, content, mimetype)
        if filename:
            mimetype = attachment['Content-Type']
            del(attachment['Content-Type'])
            del(attachment['Content-Disposition'])
            attachment.add_header('Content-Disposition', 'inline',
                                  filename=filename)
            attachment.add_header('Content-Type', mimetype, name=filename)
            attachment.add_header('Content-ID', '<%s>' % filename)
        return attachment


class MailMessageManager(models.Manager):
    def get_msg(self, msg_type, lang=None):
        """
        Ensures that if there is a more specific MailMessage it is used before
        the generic MailMessage.

        Return the MailMessage instance for the given msg_type and (optionally)
        language.
        """
        msgs = MailMessage.objects.filter(type=msg_type, lang=lang)
        if msgs:
            return msgs[0]

        msgs = MailMessage.objects.filter(type=msg_type, lang='')
        if msgs:
            return msgs[0]

        msgs = MailMessage.objects.filter(type=msg_type)
        if msgs:
            return msgs[0]

        raise MailMessage.DoesNotExist(
            "Error, a required MailMessage type {0} does not exist! "
            "Aborting".format(msg_type))


class MailMessage(models.Model):
    type = models.CharField(max_length=100, choices=MAIL_MESSAGE_CHOICES,
                            unique=True)
    subject = models.CharField(max_length=150)
    body = models.TextField()
    lang = models.CharField(max_length=10, default='', blank=True,
                            help_text='Language code, if applicable')
    attachments = models.ManyToManyField('Attachment', blank=True)

    objects = MailMessageManager()

    class Meta:
        verbose_name = 'E-mail template'
        verbose_name_plural = 'E-mail template'

    def __unicode__(self):
        return self.type

    def clean(self):
        for fieldname in MAIL_MESSAGE_REQUIRED_FIELDS[self.type]:
            if not fieldname in self.body:
                raise ValidationError(
                    "Mandatory field: {{{{ {0} }}}} is not added to this "
                    "template.".format(fieldname))

    def get_msg(self, recipient, context, subject_template=None,
                body_template=None):
        from_email = settings.DEFAULT_FROM_EMAIL

        if not subject_template:
            subject_template = self.subject

        if not body_template:
            body_template = self.body

        # Ensure no newlines after the subject
        subject = Template(subject_template).render(Context(context)).rstrip()
        body = Template(body_template).render(Context(context))

        msg = EmailMultiRelated(subject, body, from_email, [recipient])

        if MAIL_HTML_TEMPLATE:
            html_body = render_to_string(MAIL_HTML_TEMPLATE, {'body': body})
            msg.attach_alternative(html_body, 'text/html')

        for attachment in self.attachments.all():
            msg.attach_related_file(attachment.attachment.path)

        return msg

    def send(self, recipient, context, subject_template=None,
             body_template=None):
        """
        Send an email of our type to the recipient.

        The provided context dictionary contains the variables used to render
        the body of the email.

        Optionally allows overriding of the subject and body templates, in this
        case the fields of this instance are ignored when rendering the email.
        """
        msg = self.get_msg(recipient, context, subject_template, body_template)
        msg.send()


class Attachment(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False)
    attachment = models.FileField(
        upload_to=UploadTo('attachments'), null=False, blank=False)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name
