from django.utils.datastructures import SortedDict
from django.forms.widgets import CheckboxSelectMultiple, CheckboxInput
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class CheckboxSelectMultipleCategoriesTree(CheckboxSelectMultiple):
    ordering = 'order'

    def render(self, name, value, attrs=None, choices=()):
        # Ignore the queryset/pre-prepared choices and build our own with
        # child categories in the correct places.
        parent_categories = self.choices.queryset.filter(
            parent__isnull=True).order_by(self.ordering)

        nested_categories = SortedDict()
        for parent in parent_categories:
            nested_categories[parent] = self.choices.queryset.filter(
                parent__pk=parent.pk, active=True).order_by(self.ordering)

        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        # Normalize to strings
        str_values = set([force_text(v) for v in value])

        output = ['<ul>']

        def _label_for(_id_, i_):
            if _id_:
                return format_html(' for="{0}_{1}"', _id_, i_)
            return ''

        i = 0
        for parent in nested_categories:
            i += 1
            children = nested_categories[parent]
            # Append parent control.
            extra_class = 'has-children' if children else ''
            output.append('<li{}>'.format(
                ' class="{}"'.format(extra_class) if extra_class else ''))
            output.append(
                self.render_checkbox(
                    dict(final_attrs, id='{0}_{1}'.format(id_, i)), parent.pk,
                    force_text(parent), str_values, name, _label_for(id_, i),
                    bool(children)))

            # Deal with child categories.
            if children:
                output.append('<ul class="sub-filter">')
                for child in children:
                    i += 1
                    output.append('<li>')
                    output.append(
                        self.render_checkbox(
                            dict(final_attrs, id='{0}_{1}'.format(id_, i)),
                            child.pk, force_text(child), str_values, name,
                            _label_for(id_, i)))
                    output.append('</li>')
                output.append('</ul>')  # Child grouping.

            output.append('</li>')  # Parent list item.

        output.append('</ul>')
        return mark_safe('\n'.join(output))

    def render_checkbox(self, final_attrs, option_value, option_label,
                        str_values, name, label_for, has_children=False):
        cb = CheckboxInput(
            final_attrs, check_test=lambda value: value in str_values)
        option_value = force_text(option_value)
        rendered_cb = cb.render(name, option_value)
        option_label = force_text(option_label)
        if has_children:
            post_label = ' <span class="toggle-sub-categories">&nbsp;</span>'
        else:
            post_label = ''
        return u'<div class="element checkbox-container"><label{0}>' \
               u'{1} {2}</label>{3}<span class="clearfix"></span>' \
               u'</div>'.format(label_for, rendered_cb, option_label,
                                post_label)
