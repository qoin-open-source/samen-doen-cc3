import os

from django import template


register = template.Library()


@register.filter
def filename(value):
    if value:
        try:
            return os.path.basename(value.file.name)
        # might be an exception if the file can't be found
        except IOError:
            return u""

    else:
        return u""
