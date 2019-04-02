import csv
import codecs
import logging

from django.forms import modelform_factory
from django.forms.fields import DecimalField, DateField
from django.utils.translation import ugettext_lazy as _

# from cc3.core.utils.model_form import model_to_modelform


LOG = logging.getLogger('cc3.marketplace')


def validate_csv_file(attrs):
    """
    Validate the csv file upload, for the rest based serializer
    """
    # refactoring
    return process_csv_file(attrs, validate_only=True)


def process_csv_file(instance, validate_only=False):
    # importing here, to avoid circular import
    from .models import UploadInstance

    # instance can be a dict (from serializer) or model instance
    if hasattr(instance, 'file'):
        csv_file = instance.file
    else:
        csv_file = instance['file']

    # can raise exception if file in valid, caught by serializer validator
    dialect = csv.Sniffer().sniff(
        codecs.EncodedFile(csv_file, "utf-8").read(1024))

    csv_file.open()
    csv_reader = csv.DictReader(
        codecs.EncodedFile(csv_file, "utf-8"), dialect=dialect)
    if hasattr(instance, 'file'):
        file_type = instance.file_type
    else:
        file_type = instance['file_type']

    process_model = file_type.process_model

    if process_model:

        # dynamically make a ModelForm for the file_type process_model
        process_model_class = process_model.model_class()

        if file_type.clear_before_process:
            # clear
            process_model_class.objects.all().delete()

        allow_duplicates = file_type.allow_duplicates
        instance_identifier = file_type.instance_identifier

        for row in csv_reader:
            # process row of csv file
            process_model_instance = existing_model_instances = None
            model_fields = process_model_class._meta.get_all_field_names()
            if 'children' in model_fields:
                model_fields.remove('children')
            if 'parent_id' in model_fields:
                model_fields.remove('parent_id')
            model_form = modelform_factory(
                process_model_class, fields=model_fields)

            # try and identify existing instance
            try:
                kwargs = {instance_identifier: row[instance_identifier]}
                LOG.debug(u"Looking for {0}: {1}".format(
                    instance_identifier, kwargs[instance_identifier]))
                existing_model_instances = \
                    process_model.model_class().objects.filter(**kwargs)
            except Exception, e:
                LOG.debug(u"No existing_model_instance for {0} [{1}]".format(
                    kwargs, e))
                pass

            if not allow_duplicates and existing_model_instances.count() > 0:
                # in theory should only ever been zero / one existing instance
                # if no duplicates allowed!
                process_model_instance = existing_model_instances[0]

            model_form_instance = model_form(
                instance=process_model_instance, data=row)

            for _field in model_form_instance.fields:
                # using type rather than isinstance as exact class match needed
                if type(model_form_instance.fields[_field]) == DecimalField:
                    localized_field = model_form_instance.fields[_field]
                    localized_field.localize = True
                    model_form_instance.field = localized_field
            if model_form_instance.is_valid() and not validate_only:
                new_instance = model_form_instance.save()

                # if a new_instance has saved (depending on overrides of model
                # save() methods with business logic)
                if new_instance.id:
                    if allow_duplicates and \
                                    existing_model_instances.count() > 0:
                        try:
                            new_instance.handle_duplicates(
                                existing_model_instances)
                        except Exception:
                            LOG.warn(
                                _(u"No handle_duplicate method on process model"
                                  u" class for file upload {0}".format(
                                    file_type)))
                            pass

                    UploadInstance.objects.create(
                        upload=instance,
                        content_type=process_model,
                        object_id=new_instance.id
                    )
            else:
                if model_form_instance.errors:
                    raise Exception(model_form_instance.errors)
    else:
        LOG.info(_(u"No process model class for file upload {0}".format(
            file_type)))

    return instance

# TODO: cope with unicode!


def _get_csv_reader(filename, delimiters=None):
    csvfile = open(filename, 'rU')
    try:
        dialect = csv.Sniffer().sniff(csvfile.read(1024), delimiters)
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect=dialect)
        return reader
    except Exception as e:
        LOG.error("_get_csv_reader reported invalid file: {0}".format(
            e.message))
        return False


def is_valid_csv_file(filename, delimiters=None):
    """Returns True or False"""
    if _get_csv_reader(filename, delimiters):
        return True
    return False


def get_csv_row(filename, delimiters=None):
    """Returns first row of file"""
    reader = _get_csv_reader(filename, delimiters)
    return reader.next()


def get_csv_max_columns(filename, delimiters=None):
    """Returns max number of items per row"""
    reader = _get_csv_reader(filename, delimiters)
    return max([len(row) for row in reader])


def read_csv(filename, delimiters=None, skip_rows=0):
    """Generator, yielding rows from csv"""
    reader = _get_csv_reader(filename, delimiters)
    for row in reader:
        if skip_rows > 0:
            skip_rows -= 1
        else:
            # r = [unicode(cell, 'utf-8') for cell in row]
            # LOG.debug("read_csv stripped row: {0}".format(r))
            # yield r
            yield row
