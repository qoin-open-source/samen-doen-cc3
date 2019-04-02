import os
import tempfile
import xlwt

from django.conf import ImproperlyConfigured
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet, ValuesQuerySet
from django.http import HttpResponse
from django.template.defaultfilters import slugify

from .utils import filter_queryset, generate_xls, generate_csv


MAX_XLS_ROWS = 65536


class InvalidData(Exception):
    pass


class XLSIncompatible(Exception):
    pass


def admin_export_xls(request, app, model):
    """
    Adds output of admin list views to any model which uses the excelexport/change_list.html
    as a base for its admin change_list
    """
    mc = ContentType.objects.get(app_label=app, model=model).model_class()
    wb = xlwt.Workbook()
    ws = wb.add_sheet(unicode(mc._meta.verbose_name_plural[:31]))
    for i, f in enumerate(mc._meta.fields):
        ws.write(0,i, f.name)
    qs = mc.objects.all()
    qs = filter_queryset(qs, request)
    for ri, row in enumerate(qs):
        for ci, f in enumerate(mc._meta.fields):
            ws.write(ri+1, ci, unicode(getattr(row, f.name)))
    fd, fn = tempfile.mkstemp()
    os.close(fd)
    wb.save(fn)
    fh = open(fn, 'rb')
    resp = fh.read()
    fh.close()
    response = HttpResponse(resp, content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s.xls' % \
          (unicode(slugify(mc._meta.verbose_name_plural)),)
    return response


class BaseSpreadsheetResponse(HttpResponse):
    content_type = None
    file_extension = None

    def __init__(self, data, output_name='spreadsheet_data', headers=None,
                 encoding='utf8', header_override=None, **kwargs):
        content = self.generate_output(data, headers, encoding, header_override=header_override)
        content.seek(0)
        super(BaseSpreadsheetResponse, self).__init__(
            content=content.getvalue(), content_type=self.get_content_type())
        self['Content-Disposition'] = 'attachment;filename="%s.%s"' % \
            (output_name.replace('"', '\"'), self.get_file_extention())

    def clean(self, data, headers, header_override=None, *args, **kwargs):
        # Make sure we've got the right type of data to work with and adjust
        # headers.
        valid_data = False
        if isinstance(data, ValuesQuerySet):
            data = list(data)
        elif isinstance(data, QuerySet):
            data = list(data.values())
        if hasattr(data, '__getitem__'):
            if len(data) > 0 and isinstance(data[0], dict):
                if headers is None:
                    headers = data[0].keys()
                data = [[row[col] for col in headers] for row in data]
                if header_override is not None:
                    data.insert(0, header_override)
                else:
                    data.insert(0, headers)
            if len(data) > 0 and hasattr(data[0], '__getitem__'):
                valid_data = True

        if not valid_data:
            raise InvalidData("Sequence of sequences required.")
        return data

    def generate_output(self, data, headers, encoding, header_override=None, *args, **kwargs):
        # Make sure you call `clean()` when implementing. E.g.:
        # data = self.clean(data, headers)
        raise NotImplementedError

    def get_content_type(self):
        # Use self.mimetype if no content_type supplied
        # (for backward compatibilty)
        if self.content_type is None:
            if self.mimetype is None:
                raise ImproperlyConfigured
            return self.mimetype
        return self.content_type

    def get_file_extention(self):
        if self.file_extension is None:
            raise ImproperlyConfigured
        return self.file_extension


class CSVResponse(BaseSpreadsheetResponse):
    """
    Response that offers a CSV file for download.
    """
    content_type = 'text/csv'
    file_extension = 'csv'

    def generate_output(self, data, headers, encoding, header_override=None):
        # `clean()` is called to prepare the data and check for validation
        # errors.
        data = super(CSVResponse, self).clean(data, headers, header_override)
        return generate_csv(data, headers, encoding)


class ExcelResponse(BaseSpreadsheetResponse):
    """
    Response that offers an Excel spreadsheet for download.

    Can be used with any sequence of sequences including results from a raw SQL
    query and a QuerySet.

        cursor = connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

        return ExcelResponse(rows, output_name=output_name)
    """
    content_type = 'application/vnd.ms-excel'
    file_extension = 'xls'

    def clean(self, data, headers, header_override=None):
        data = super(ExcelResponse, self).clean(data, headers, header_override)
        if len(data) > MAX_XLS_ROWS:
            raise XLSIncompatible("Too many rows for Excel.")
        return data

    def generate_output(self, data, headers, encoding, header_override=None):
        # `clean()` is called to prepare the data and check for validation
        # errors.
        data = self.clean(data, headers, header_override)
        return generate_xls(data, headers, encoding)


class SpreadsheetResponse(ExcelResponse):
    """
    Response that favours Excel as an output format but fallsback to CSV if
    validation fails for Excel.
    """
    def generate_output(self, data, headers, encoding, header_override=None):
        try:
            data = self.clean(data, headers, header_override)
            output_func = generate_xls
        except XLSIncompatible:
            # Re-set content_type and extension to CSV.
            self.content_type = CSVResponse.content_type
            self.file_extension = CSVResponse.file_extension
            output_func = generate_csv

        return output_func(data, headers, encoding)
