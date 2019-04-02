import base64
import os
from os import path as os_path
import random
import sha

from django.conf import settings
from django.db.models.fields import FieldDoesNotExist
from django.template.defaultfilters import slugify

# converted fileupload callback to deconstructible class
# see https://code.djangoproject.com/ticket/22999 - issue with
# changes to migration framework
from django.utils.deconstruct import deconstructible

RANDOM_BYTES = 64


@deconstructible
class UploadTo(object):

    def __init__(self, sub_path, attribute=None):
        self.sub_path = sub_path
        self.attribute = attribute

    def __call__(self, instance, filename):
        if self.attribute:
            return os_path.join(
                self.sub_path, unicode(
                    slugify(getattr(instance, self.attribute))), filename)
        else:
            return os_path.join(
                self.sub_path, get_verification_docs_folder_name(), filename)


@deconstructible
class UploadToSecure(object):

    def __init__(self, sub_path):
        self.sub_path = sub_path

    def __call__(self, instance, filename):
        return os_path.join(
            self.sub_path, get_verification_docs_folder_name(), filename)


# def get_upload_to(path, attribute=None):
#     def upload_callback(instance, filename):
#         if attribute:
#             return os_path.join(
#                 path, unicode(slugify(getattr(instance, attribute))),
# filename)
#         else:
#             return os_path.join(path, filename)
#
#     return upload_callback


def handle_uploaded_file(f, file_path):
    """
    Save an uploaded file to a file path
    """
    file_path_on_disc = os_path.join(settings.MEDIA_ROOT, file_path)

    with open(file_path_on_disc, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def get_image_filename(instance, filename, folder_name='images'):
    """
    Where instance is a model instance.

    NB, not used directly by model ImageField, even though it's specified.
    Need to use the 'upload_to' ImageField attribute in the form instead, or
    handle_uploaded_file
    """
    filepath_to_check_folder = os_path.join(settings.MEDIA_ROOT, folder_name)
    image_count = 0

    while os_path.exists(get_file_path(
            filepath_to_check_folder, instance.id, image_count)):
        image_count += 1

    fp = get_file_path(folder_name, instance.id, image_count)
    return fp


def get_file_path(folder, instance_id, image_count):
    return "%s/%s_%s.jpg" % (
        folder, instance_id, '%(#)06d' % {'#': image_count})


def get_currency_symbol():
    return getattr(settings, "CURRENCY_SYMBOL", "Q")


def has_field(model, field_name):
    try:
        model._meta.get_field_by_name(field_name)
        return True
    except FieldDoesNotExist:
        return False


def instance_from_kwargs(model, **kwargs):
    """Return an instance of model using kwargs that match field names."""
    return model(**{
        k: v for k, v in kwargs.iteritems() if has_field(model, k)
    })


def get_verification_docs_folder_name():

    fullpath = None

    for i in range(2):
        try:
            r = os.urandom(RANDOM_BYTES)
        except NotImplementedError:
            data = [random.randrange(256) for n in xrange(RANDOM_BYTES)]
            r = ''.join(map(chr, data))
        prefix = base64.urlsafe_b64encode(sha.new(r).digest())[:16]
        fullpath = os.path.join(settings.VERIFICATION_DOCUMENTS_ROOT, prefix)
        try:
            os.mkdir(fullpath)
        except IOError:
            if i == 0:
                continue
            raise

    return fullpath
