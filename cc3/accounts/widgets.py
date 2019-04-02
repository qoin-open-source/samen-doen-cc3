
from itertools import chain

from django.forms.widgets import CheckboxSelectMultiple, CheckboxInput
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


class ToggleSelectMultiple(CheckboxSelectMultiple):

    class Media:
        css = {
            'all': ('css/onoffswitch.css',)
        }

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []
        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        output = []
        # Normalize to strings
        str_values = set([force_text(v) for v in value])
        for i, (option_value, option_label) in enumerate(
                chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if id_:
                final_attrs = dict(final_attrs, id=u'{0}_{1}'.format(id_, i))
                label_for = format_html(u' for="{0}_{1}"', id_, i)
            else:
                label_for = u''
            output.append(self.render_checkbox(
                final_attrs, option_value, option_label, str_values, name,
                label_for))
        return mark_safe('\n'.join(output))

    def render_checkbox(self, final_attrs, option_value, option_label,
                        str_values, name, label_for, has_children=False):

        cb = CheckboxInput(final_attrs, check_test=lambda value:
                           value in str_values)
        option_value = force_text(option_value)
        rendered_cb = cb.render(name, option_value)
        option_label = force_text(option_label)

        return u'''<div class="onoffswitch-wrapper">
                %s
                <div class="onoffswitch-wrap">
                    <div class="onoffswitch-text">%s</div>
                    <div class="onoffswitch">
                        %s
                        <label class="onoffswitch-label" %s>
                            <div class="onoffswitch-inner"></div>
                            <div class="onoffswitch-switch"></div>
                        </label>
                    </div>
                    <div class="onoffswitch-text">%s</div>
                </div>
            </div>
            <br clear="all" />
        ''' % (
            option_label, _(u'unblocked'), rendered_cb,
            label_for, _(u'blocked')
        )


#  {% static 'images/icons/dummy_card_icon.png' %}
