# encoding: utf-8
from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _


# Default max file size in MB
DEFAULT_MAX_FILE_SIZE = 1

# Default accepted formats
DEFAULT_VALID_FILE_FORMATS = [
    'pdf', 'jpg', 'jpeg',
    'png'
]

MB = 1000 * 1000


def req(field):
    return "".join([_(u'The field '), ' ', field, ' ', _(u' is required.')])


class RestrictiveFileField(forms.FileField):

    def __init__(self, *args, **kwargs):

        internal_kwargs = ['max_file_size', 'valid_file_formats']
        kwargs_local = {}

        for kwarg in internal_kwargs:
            if kwargs.has_key(kwarg):
                kwargs_local[kwarg] = kwargs.pop(kwarg)

        super(RestrictiveFileField, self).__init__(*args, **kwargs)

        try:
            self.max_file_size = settings.MAX_FILE_SIZE
        except AttributeError:
            self.max_file_size = DEFAULT_MAX_FILE_SIZE

        try:
            self.valid_file_formats = settings.VALID_FILE_FORMATS
        except AttributeError:
            self.valid_file_formats = DEFAULT_VALID_FILE_FORMATS

        self.max_file_size = kwargs_local.get(
            'max_file_size', self.max_file_size) * MB
        self.valid_file_formats = kwargs_local.get(
            'valid_file_formats', self.valid_file_formats)

    def clean(self, *args, **kwargs):
        upload = super(RestrictiveFileField, self).clean(*args, **kwargs)

        if not upload:
            return upload

        if not(upload.name.split('.')[-1].lower() in self.valid_file_formats):
            raise forms.ValidationError(
                (_(u'Only the following file formats are allowed: ') +
                  (', '.join(self.valid_file_formats))))
        try:
            if upload.size > self.max_file_size:
                raise forms.ValidationError(

                    (_(u'The maximum allowed file size is: {0}MB').format(
                        self.max_file_size/MB)))
        except OSError:

            # Indicates an error occurred reading the
            # uploaded file
            raise forms.ValidationError(
                _(u'An error occurred reading the uploaded file'))

        return upload
