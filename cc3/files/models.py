import datetime
import json
import logging

from cc3.core.utils import UploadTo
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

# from cc3.core.utils import get_upload_to
from cc3.cyclos.models import User
from cc3.rules.models import RuleSet

from .utils import process_csv_file


LOG = logging.getLogger(__name__)

UPLOAD_STATUS_CHOICES = (
    ('Uploaded', _('Uploaded')),
    # ('Valid', _('Valid')), # only ever uploaded if valid
    #    ('Invalid', _('Invalid')),  # never saved if invalid
    ('Processed', _('Processed')),
)


# if not getattr(settings, 'UPLOAD_MODELS', ''):
# MODELS = [(m.id, '%s.%s' % (m._meta.app_label, m.__name__) )
#         for m in models.loading.get_models()
#         if m._meta.app_label != 'contenttypes'
#     ]
# else:
#     MODEL_NAMES = deepcopy(settings.UPLOAD_MODELS)
#     MODELS = []
#     for m in MODEL_NAMES:
#         app_label = m[:m.rfind('.')]
#         model = m[m.rfind('.')+1:]
#         MODELS.append((
#             ContentType.objects.get(app_label=app_label, model=model).id,
#             model
#         ))

#    MODELS = [(ContentType.objects.get(app_label=,
#                                       model=m[m.rfind('.')+1].lower()), m)
#              for m in MODEL_NAMES]

# MODELS = tuple([(ContentType.objects.get(m).id, m) for m in MODELS])


class Format(models.Model):
    """
    File Format
    """
    description = models.CharField(
        max_length=255, help_text=_('Description of the file format'))
    mime_type = models.CharField(
        max_length=100, help_text=_('Expected MIME type of the file'))
    extension = models.CharField(
        max_length=10, help_text=_('Expected file extension for type'))

    def __unicode__(self):
        return self.description


class FileType(models.Model):
    """
    File Type - type in this case is really a description rather than any
    programming construct!
    [nb had to add File to name as Type is obviously a reserved word in python]
    """
    description = models.CharField(
        max_length=255, help_text=_('Description of the file type'))
    format = models.ForeignKey('Format')

    # TODO restrict these content types in settings
    process_model = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        help_text=_(u'If set, validate and if not testint, save data from file'
                    u' to model instances of this type'))

    instance_identifier = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_(u"name of (heading) field in process_model to be used as "
                    u"identifier for get_or_create on import")
    )

    filetypeset = models.ForeignKey('FileTypeSet', blank=True, null=True)

    clear_before_process = models.BooleanField(
        default=True, help_text=_(u"Empty temp table before uploading data "
                                  u"from file?"))
    allow_duplicates = models.BooleanField(
        default=True, help_text=_(u"If True, duplicate instance sent to "
                                  u"model.handle_duplicate() post creation"))

    def __unicode__(self):
        return self.description


class Upload(models.Model):
    """
    Record of an instance of a file upload.
    """
    file_type = models.ForeignKey('FileType')
    file = models.FileField(
        upload_to=UploadTo('uploaded_files', 'id'), max_length=500)
    # get_upload_to('uploaded_files', 'id')
    date_created = models.DateTimeField(
        _(u'Date created'), auto_now_add=True)
    user_created = models.ForeignKey(User)
    status = models.CharField(
        _('Status'),
        max_length=10,
        choices=UPLOAD_STATUS_CHOICES,
        default=UPLOAD_STATUS_CHOICES[0][0]  # 'Uploaded'
    )

    def __unicode__(self):
        return u"%s (%s - %s)" % (self.file, self.file_type, self.date_created)


class UploadInstance(models.Model):
    upload = models.ForeignKey(Upload, editable=False)
    content_type = models.ForeignKey(ContentType, editable=False)
    object_id = models.PositiveIntegerField(editable=False)
    content_object = fields.GenericForeignKey('content_type', 'object_id')
    status = models.CharField(
        _('Status'),
        max_length=10,
        choices=UPLOAD_STATUS_CHOICES,
        default=UPLOAD_STATUS_CHOICES[0][0]  # 'Uploaded'
    )

    def __unicode__(self):
        return u"%s (%s)" % (self.content_type, self.status)


class FileServiceUser(models.Model):
    """
    Files service User who can upload files using a specific token
    """
    user = models.ForeignKey(User)
    ip_addresses = models.CharField(
        max_length=255,
        help_text=_("Optional list of ip4 ip addresses (comma delimited) where"
                    " user can access service from"),
        blank=True
    )

    def __unicode__(self):
        if self.ip_addresses:
            return u"%s (%s)" % (self.user, self.ip_addresses)
        else:
            return u"%s" % self.user

    def check_ip_address(self, ip_address):
        """
        :param ip_address: IP address of remote user
        :return: True if ip address is valid
        """
        if self.ip_addresses:
            ip_addresses = self.ip_addresses.split(',')
            for ip in ip_addresses:
                if ip_address == ip.strip():
                    return True

            return False

        return True


class FileTypeSet(models.Model):
    name = models.CharField(
        _(u'File Type Set'),
        max_length=255,
        help_text=_('Name of group of file types which can be processed '
                    'together')
    )

    ruleset = models.ForeignKey(
        RuleSet, blank=True, null=True,
        help_text=_(u"Which set of rules should be used to process these "
                    u"files"))

    email_addresses = models.TextField(
        blank=True, default='',
        help_text=_(u'Email addresses (comma separated) where an Excel report '
                    u'should be sent'))

    def __unicode__(self):
        return self.name

    def run_ruleset(self):
        """ Run set of rules associated with this set of files. """

        # need pairs (for now) of instances for each entry in the temp tables
        file_types = FileType.objects.filter(filetypeset=self)
        upload_ids = []
        upload_instance_ids = []
        instances = {}
        rule_results = []

        # TODO we really need pairs (or sets) of instances, this provides a way but with the true instances
        # TODO may be better to have ids and content types and get instances when processing?
        for file_type in file_types:
            instance_identifier = file_type.instance_identifier

            # get unprocessed rows for file_type process_model
            upload_instances = UploadInstance.objects.filter(
                upload__file_type=file_type,
                status=UPLOAD_STATUS_CHOICES[0][0]
            )

            for upload_instance in upload_instances:
                upload_id = upload_instance.upload.id
                if not upload_id in upload_ids:
                    upload_ids.append(upload_id)
                upload_instance_ids.append(upload_instance.id)
                instance = upload_instance.content_object
                if hasattr(instance, instance_identifier):
                    _id = getattr(instance, instance_identifier)
                    # create a list for the key if it doesn't exist
                    if not _id in instances:
                        instances[_id] = []
                    instances[_id].append(instance)

        for key, value in instances.iteritems():
            # each value is a row containing content_object values linked by
            # the instance identifier (key)
            # RUN THE RULES for the ruleset
            rule_results.append(self.ruleset.run(value))

            # mark upload instances as processed
            for val in value:
                upload_instances = UploadInstance.objects.filter(
                    upload__id__in=upload_ids,
                    content_type=ContentType.objects.get_for_model(val),
                    object_id=val.id
                )
                for upload_instance in upload_instances:
                    upload_instance.status = UPLOAD_STATUS_CHOICES[1][0]
                    upload_instance.save()

        # mark uploads instances as processed
        for upload_id in upload_ids:
            upload = Upload.objects.get(pk=upload_id)
            upload.status = UPLOAD_STATUS_CHOICES[1][0]
            upload.save()

        # store results, so project specific signal can send a report as
        # necessary
        FileTypeSetRun.objects.create(
            filetypeset=self,
            rule_results=json.dumps(rule_results)
        )


class FileTypeSetRun(models.Model):
    filetypeset = models.ForeignKey('FileTypeSet')
    rule_results = models.TextField()


@receiver(post_save, sender=Upload, dispatch_uid='cc3_files_upload')
def process_file_upload(sender, instance, created, **kwargs):
    """
    Once an upload of a file has been completed, run any necessary post
    processing of the file to save data to specified model instances.
    """
    if created:
        if instance.file_type.format.description == u'CSV file':
            return process_csv_file(instance)
        else:
            raise NotImplementedError
