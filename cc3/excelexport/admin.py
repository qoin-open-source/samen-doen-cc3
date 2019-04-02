import operator
import os
import tempfile
import xlwt

from django.conf import settings
from django.http import HttpResponse
from django.template.defaultfilters import slugify

from .utils import get_object_from_name, get_fully_qualified_classname


# Function to generate an XLS file based on a queryset
# Called as a Django admin action
# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal,PyUnusedLocal,
# PyUnusedLocal,PyProtectedMember
# #3061 Modified to take optional global and field-specific content and
# style-related configuration
def admin_action_export_xls(modeladmin, request, queryset):
    """
    Add as an action for ModelAdmin classes to export the queryset to XLS.
    """
    # Initialize some variables specific to handling fields specified via
    # settings
    positions = {}
    styles = {'none_style': xlwt.easyxf('')}
    # For global field conf (by type). Global conf takes precedence on field
    # specific conf.
    global_fmt = {}
    global_styles = {}
    global_filters = {}
    fields = {}
    filters = {}
    col_width = None

    # Get global field configuration
    if hasattr(settings, 'ADMIN_ACTION_EXPORT_XLS_FIELDS') and \
            'global' in settings.ADMIN_ACTION_EXPORT_XLS_FIELDS:
        global_fmt = settings.ADMIN_ACTION_EXPORT_XLS_FIELDS['global']

    model_fqn = get_fully_qualified_classname(queryset.model)

    # Check for the presence of a specification for the model in the app settings
    if hasattr(settings, 'ADMIN_ACTION_EXPORT_XLS_FIELDS') and \
            model_fqn in settings.ADMIN_ACTION_EXPORT_XLS_FIELDS:
        # Get the field conf. corresponding to the model from the settings
        field_conf = settings.ADMIN_ACTION_EXPORT_XLS_FIELDS[model_fqn]

        if 'fields' in field_conf:
            # Get the fields configuration
            fields = field_conf['fields']

        if fields:
            # Note that positions specified in
            positions = {fields[f]['position']: f for f in fields if 'position' in fields[f]}

        if 'col_width' in field_conf:
            # Get the column width
            col_width = int(field_conf['col_width'])

    # If no queryset model specific column width, use global setting
    if not col_width and global_fmt:
        if 'col_width' in global_fmt:
            col_width = int(global_fmt['col_width'])

    # Get the model meta data
    model_meta = queryset.model._meta

    # Create a new excel workbook and initialize it with a new spreadsheet
    wb = xlwt.Workbook()
    ws = wb.add_sheet(unicode(model_meta.verbose_name_plural[:31]))

    # For loop counter used to add extra fields
    index = 0
    for i, f in enumerate(model_meta.fields):
        # Handle field insertion from settings file
        while index in positions:
            ws.write(0, index, positions[index])
            index += 1

        ws.write(0, index, f.name)
        index += 1

    # Handle any field whose position comes after after the end
    # of the model_meta.fields collection
    while index in positions:
        ws.write(0, index, positions[index])
        index += 1

    # Write the actual field values
    # For each row in the queryset
    for ri, row in enumerate(queryset):
        index = 0

        # For each field
        for ci, f in enumerate(model_meta.fields):
            # Handle field insertion from settings file
            while index in positions:
                # Get the field name
                field_name = positions[index]

                try:
                    # Get the attribute specified in the settings.
                    # Uses dot notation, thus the use of operator.attrgetter
                    value = operator.attrgetter(fields[field_name]['attr'])(row)
                except KeyError:
                    continue

                # Blank global config for current field
                global_field_cfg = None

                # First check global config
                # Get the field type
                fqn = get_fully_qualified_classname(type(value))

                # The global field config for the field fqn
                global_field_cfg = get_global_field_config(global_fmt, fqn)

                # Get the filter object from the appropriate source
                filter_obj = get_filter_obj(field_name, fqn, global_filters, global_field_cfg, filters, fields)

                # If there is a filter for this field
                if filter_obj:
                    value = filter_obj.apply(value)

                # Get the style for the field from the appropriate source
                style = get_style(field_name, fqn, global_styles, global_field_cfg, styles, fields)

                # Get unicode config for the fields
                is_unicode = is_field_unicode(field_name, global_field_cfg, fields)

                if is_unicode:
                    # Write the field value to the file using the relevant style information
                    ws.write(ri + 1, index, unicode(value), style)
                else:
                    ws.write(ri + 1, index, value, style)

                # Tackle the next field
                index += 1

            # Get the field value
            value = getattr(row, f.name)

            # First check global config
            # Get the field type
            fqn = get_fully_qualified_classname(type(value))

            # The global field config for the field fqn
            global_field_cfg = get_global_field_config(global_fmt, fqn)

            # Get the filter object from the appropriate source
            filter_obj = get_filter_obj(f.name, fqn, global_filters, global_field_cfg, filters, fields)

            if filter_obj:
                value = filter_obj.apply(value)

            # Get the style for the field from the appropriate source
            style = get_style(f.name, fqn, global_styles, global_field_cfg, styles, fields)

            is_unicode = is_field_unicode(f.name, global_field_cfg, fields)

            if is_unicode:
                ws.write(ri + 1, index, unicode(value), style)
            else:
                ws.write(ri + 1, index, value, style)
            index += 1

        # Handle any field whose position comes after after the end
        # of the model_meta.fields collection
        while index in positions:
            # Get the current field name
            field_name = positions[index]

            # Get the field value
            value = operator.attrgetter(fields[field_name]['attr'])

            # First check global config
            # Get the field type
            fqn = get_fully_qualified_classname(type(value))

            # The global field config for the field fqn
            global_field_cfg = get_global_field_config(global_fmt, fqn)

            # Initialize the filter object
            filter_obj = None

            # Get the filter object from the appropriate source
            filter_obj = get_filter_obj(field_name, fqn, global_filters, global_field_cfg, filters, fields)

            # Get the attribute specified in the settings.
            # Uses dot notation, thus the use of operator.attrgetter
            is_unicode = is_field_unicode(field_name, global_field_cfg, fields)

            try:
                if is_unicode:
                    ws.write(ri+1, index, unicode(operator.attrgetter(fields[field_name]['attr'])(row)))
                else:
                    ws.write(ri + 1, index, operator.attrgetter(fields[field_name]['attr'])(row))
            except (KeyError, TypeError):
                pass
            index += 1

    # set the column width
    if col_width:
        for i in range(index):
            ws.col(i).width = int(col_width * 260)

    fd, fn = tempfile.mkstemp()
    os.close(fd)
    wb.save(fn)
    fh = open(fn, 'rb')
    resp = fh.read()
    fh.close()
    response = HttpResponse(resp, content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s.xls' % \
        (unicode(slugify(model_meta.verbose_name_plural)),)
    return response


# #3061 Utility function that returns a filter object given
# A global_filters dictionary used to store reusable filters (will add to it if applicable)
# The fully qualified class name of the field type
# A global_field_cfg dictionary that contains the global config for this field type
# A filters dictionary that contains the saved filters per specific field
# A field_cfg dictionary containing the field specific configuration from the app settings
def get_filter_obj(field_name, fqn, global_filters, global_field_cfg, filters, fields_cfg):
    filter_obj = None
    # Check if there is a filter specified for that field
    # First look if a global filter for that field type has been saved
    if global_filters and fqn in global_filters:
        filter_obj = global_filters[fqn]
    # If no global filter saved, look if there is global filter conf information available
    # and save it for other fields/cells of the same type
    elif global_field_cfg and 'filter' in global_field_cfg:
        filter_obj = get_object_from_name(global_field_cfg['filter'])
        global_filters[fqn] = filter_obj
    # if no global filter specified for this field type
    # look for field-specific saved filter information
    elif filters and field_name in filters:
        filter_obj = filters[field_name]
    # Otherwise check if there is field-specific config information
    # If so save it for future similar cells/fields
    elif fields_cfg and field_name in fields_cfg and 'filter' in fields_cfg[field_name]:
        filter_obj = get_object_from_name(fields_cfg[field_name]['filter'])
        filters[field_name] = filter_obj
    return filter_obj


# #3061 Utility function for retrieving the global config for a field type given
# The global_fmt formatting configuration dictionary created from the app settings
# A field type fqn (fully qualified name)
def get_global_field_config(global_fmt, fqn):
    global_field_cfg = None
    # If there is global field conf info
    # AND there is a 'field' key
    if global_fmt and 'fields' in global_fmt:
        # If there is conf info for the given field type
        if fqn in global_fmt['fields']:
            # Retrieve the conf info for that field type
            global_field_cfg = global_fmt['fields'][fqn]
    return global_field_cfg


# #3061 Utility function for getting a style from the appropriate source
def get_style(field_name, fqn, global_styles, global_field_cfg, styles, fields):
    style = None
    num_format_str = None
    style_str = None

    # Check if there is a style saved for this type of field
    if global_styles and fqn in global_styles:
        style = global_styles[fqn]
    # If not, look for global config
    elif global_field_cfg:
        if 'num_format' in global_field_cfg:
            num_format_str = global_field_cfg['num_format']
        if 'style' in global_field_cfg:
            style_str = global_field_cfg['style']
        if num_format_str or style_str:
            style = xlwt.easyxf(style_str, num_format_str=num_format_str)
            global_styles[fqn] = style

    # If no global style saved or found in app settings
    # look if there is style saved for the specific field
    if not style and field_name in styles:
        style = styles[field_name]

    # If no style saved for the specific field, look in app settings
    if not style and field_name in fields:
        if 'num_format' in fields[field_name]:
            num_format_str = fields[field_name]['num_format']
        if 'style' in fields[field_name]:
            style_str = fields[field_name]['style']
        if num_format_str or style_str:
            style = xlwt.easyxf(style_str, num_format_str=num_format_str)
            styles[field_name] = style

    # If no style information found, apply no style
    if not style:
        style = styles['none_style']

    return style


# #3061 Utility function to determine from global field type conf or field-specific conf
# whether a field should be set as a unicode string
def is_field_unicode(field_name, global_field_cfg, fields):
    is_unicode = True
    if global_field_cfg and 'unicode' in global_field_cfg:
        is_unicode = global_field_cfg['unicode']
    elif field_name in fields and 'unicode' in fields[field_name]:
        is_unicode = fields[field_name]['unicode']
    return is_unicode

admin_action_export_xls.short_description = "Export to XLS"
