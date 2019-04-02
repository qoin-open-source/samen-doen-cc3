import csv
import datetime
import StringIO

import xlwt

from django.conf import settings
from django.contrib.admin.options import IncorrectLookupParameters
from django.utils.encoding import smart_str

from importlib import import_module

# Changelist settings
ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
TO_FIELD_VAR = 't'
IS_POPUP_VAR = 'pop'
ERROR_FLAG = 'e'
# END from django.contrib.admin.views.main:

CSV_SEPARATOR = getattr(settings, "CSV_SEPARATOR", ",")


def get_lookup_params(request):
    lookup_params = dict(request.GET.items())
    for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR):
        if i in lookup_params:
            del lookup_params[i]
    for key, value in lookup_params.items():
        if not isinstance(key, str):
            # 'key' will be used as a keyword argument later, so Python
            # requires it to be a string.
            del lookup_params[key]
            lookup_params[smart_str(key)] = value

        # if key ends with __in, split parameter into separate values
        if key.endswith('__in'):
            lookup_params[key] = value.split(',')

        # if key ends with __isnull, special case '' and false
        if key.endswith('__isnull'):
            if value.lower() in ('', 'false'):
                lookup_params[key] = False
            else:
                lookup_params[key] = True
    return lookup_params


def filter_queryset(qs, request):
# from django.contrib.admin.views.main [reworked v slightly]:
    lookup_params = get_lookup_params(request)

    # Apply lookup parameters from the query string.
    try:
        qs = qs.filter(**lookup_params)
        # Naked except! Because we don't have any other way of validating "params".
        # They might be invalid if the keyword arguments are incorrect, or if the
        # values are not in the correct type, so we might get FieldError, ValueError,
        # ValicationError, or ? from a custom field that raises yet something else
        # when handed impossible data.
    except:
        raise IncorrectLookupParameters

    return qs


def generate_csv(data, headers, encoding):
    output = StringIO.StringIO()
    csv_writer = csv.writer(output, delimiter=CSV_SEPARATOR)
    for row in data:
        out_row = []
        for value in row:
            if not isinstance(value, basestring):
                value = unicode(value)
            # Strip out carriage returns and replace newlines with
            # spaces.
            value = value.replace("\r", "").replace("\n", " ")
            value = value.encode(encoding)
            out_row.append(value)
        csv_writer.writerow(out_row)

    return output


def generate_xls(data, headers, encoding):
    output = StringIO.StringIO()
    book = xlwt.Workbook(encoding=encoding)
    sheet = book.add_sheet('Sheet 1')
    styles = {
        'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
        'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
        'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
        'default': xlwt.Style.default_style,
    }
    for rowx, row in enumerate(data):
        for colx, value in enumerate(row):
            if isinstance(value, datetime.datetime):
                cell_style = styles['datetime']
            elif isinstance(value, datetime.date):
                cell_style = styles['date']
            elif isinstance(value, datetime.time):
                cell_style = styles['time']
            else:
                cell_style = styles['default']
            sheet.write(rowx, colx, value, style=cell_style)

    book.save(output)
    return output

# Given a class (as returned by type(...)), return the fully qualified name string
def get_fully_qualified_classname(obj_class):
    return obj_class.__module__ + '.' + obj_class.__name__

# Given a fully qualified name, return an object
def get_object_from_name(name):
    if name:
        parts = name.rsplit('.', 1)
        return getattr(import_module(parts[0]), parts[1])
    else:
        return None
