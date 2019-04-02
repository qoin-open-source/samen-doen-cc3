from django import template
from django.template.defaultfilters import safe

from classytags.arguments import Argument, MultiValueArgument
from classytags.core import Options, Tag

from ..models import CMSPlaceholder

register = template.Library()


class RenderIdentifier(Tag):
    """
    Given a CMS Placeholder page identifier, render the content of the placeholder field.
    """
    name = 'render_identifier'
    options = Options(
        Argument('page_identifier'),
    )

    def render_tag(self, context, page_identifier):
        request = context.get('request', None)
        if not request:
            return ''
        if not page_identifier:
            return ''
        placeholders = CMSPlaceholder.objects.filter(page_identifier=page_identifier)
        if not placeholders:
            return ""
        ph = placeholders[0]
        return safe(ph.cmscontent_placeholder.render(context, None))
register.tag(RenderIdentifier)
