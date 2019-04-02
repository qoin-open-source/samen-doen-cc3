# encoding: utf-8
from itertools import chain

from django.forms.widgets import CheckboxSelectMultiple, CheckboxInput
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from cc3.core.models import Category
from .common import AD_STATUS_ACTIVE
from .models import CampaignCategory


class PiraatCheckboxSelectMultiple(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        output = ['<ul>']
        # Normalize to strings
        str_values = set([force_text(v) for v in value])

        for i, (option_value, option_label) in enumerate(
                chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if id_:
                final_attrs = dict(final_attrs, id='{0}_{1}'.format(id_, i))
                label_for = format_html(' for="{0}_{1}"', id_, i)
            else:
                label_for = ''
            output.append(self.render_checkbox(
                final_attrs, option_value, option_label, str_values, name,
                label_for))
        output.append('</ul>')

        return mark_safe('\n'.join(output))

    def render_checkbox(self, final_attrs, option_value, option_label,
                        str_values, name, label_for):
        checkbox = CheckboxInput(
            final_attrs, check_test=lambda value: value in str_values)
        option_value = force_text(option_value)
        rendered_cb = checkbox.render(name, option_value)
        option_label = force_text(option_label)

        return format_html(
            '<li><div class="element checkbox-container"><label{0}>'
            '{1} {2}</label></div></li>', label_for, rendered_cb, option_label)


class PiraatSidebarCheckboxSelectMultiple(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        output = ['<ul>']
        # Normalize to strings
        str_values = set([force_text(v) for v in value])

        for i, (option_value, option_label) in enumerate(chain(
                self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if id_:
                final_attrs = dict(final_attrs, id='{0}_{1}'.format(id_, i))
                label_for = format_html(' for="{0}_{1}"', id_, i)
            else:
                label_for = ''
            output.append(self.render_checkbox(
                final_attrs, option_value, option_label, str_values, name,
                label_for))
        output.append('</ul>')

        return mark_safe('\n'.join(output))

    def render_checkbox(self, final_attrs, option_value, option_label,
                        str_values, name, label_for):
        checkbox = CheckboxInput(
            final_attrs, check_test=lambda value: value in str_values)
        option_value = force_text(option_value)
        rendered_cb = checkbox.render(name, option_value)
        option_label = force_text(option_label)

        return format_html(
            '<li><div class="element checkbox-container"><label{0}>'
            '{1} {2}</label></div></li>', label_for, rendered_cb, option_label)


class PiraatCheckboxSelectMultipleCategoriesTree(CheckboxSelectMultiple):
    ordering = 'order'  # Was: 'title'
    category_qs = Category.objects.all()

    def render(self, name, value, attrs=None, choices=()):
        # Ignore the queryset/pre-prepared choices and build our own with
        # child categories in the correct places.
        parent_categories = self.choices.queryset.filter(
            parent__isnull=True).order_by(self.ordering)
        nested_categories = SortedDict()

        for parent in parent_categories:
            nested_categories[parent] = self.category_qs.filter(
                parent__pk=parent.pk, active=True).order_by(self.ordering)

        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        # Normalize to strings
        str_values = set([force_text(v) for v in value])

        output = ['<ul>']

        def _label_for(_id_, _i):
            if _id_:
                return format_html(' for="{0}_{1}"', _id_, _i)
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
                    force_text(parent), str_values, name,
                    _label_for(id_, i), bool(children))
            )

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
                            _label_for(id_, i))
                    )
                    output.append('</li>')
                output.append('</ul>')  # Child grouping.

            output.append('</li>')  # Parent list item.

        output.append('</ul>')
        return mark_safe('\n'.join(output))

    def render_checkbox(self, final_attrs, option_value, option_label,
                        str_values, name, label_for, has_children=False):
        checkbox = CheckboxInput(
            final_attrs, check_test=lambda value: value in str_values)
        option_value = force_text(option_value)
        rendered_cb = checkbox.render(name, option_value)
        option_label = force_text(option_label)
        if has_children:
            post_label = ' <span class="toggle-sub-categories">&nbsp;</span>'
        else:
            post_label = ''
        return u'<div class="element checkbox-container"><label{0}>' \
               u'{1} {2}</label>{3}</div>'.format(
                   label_for, rendered_cb, option_label, post_label)


class PiraatCheckboxSelectMultipleCampaignCategoriesTree(
    PiraatCheckboxSelectMultipleCategoriesTree):
    category_qs = CampaignCategory.objects.all()


class OfferWantCheckboxSelectMultiple(PiraatSidebarCheckboxSelectMultiple):
    """
    Extend Django CheckboxSelectMultiple to show numbers of 'items' next to
    choices.
    """
    def render(self, name, value, attrs=None, choices=()):
        from cc3.marketplace.models import Ad
        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        output = ['<ul>']
        # Normalize to strings
        str_values = set([force_text(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices,
                                                               choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if id_:
                final_attrs = dict(final_attrs, id='{0}_{1}'.format(id_, i))
                label_for = format_html(' for="{0}_{1}"', id_, i)
            else:
                label_for = ''

            ad_type_count = Ad.objects.filter(
                adtype__pk=option_value, status=AD_STATUS_ACTIVE).count()
            output.append(self.render_checkbox(
                final_attrs, option_value,
                u"{0} ({1})".format(_(option_label), ad_type_count),
                str_values, name, label_for))
        output.append('</ul>')

        return mark_safe('\n'.join(output))


class CommunityCheckboxSelectMultiple(PiraatSidebarCheckboxSelectMultiple):
    """
    Extend Django CheckboxSelectMultiple to show numbers of 'items' next to
    choices.
    #todo: refactor these overrides: add a method to
           PiraatSidebarCheckboxSelectMultiple for the counting.
    #todo: revisit the performance of counting these things on every render!
    """
    def render(self, name, value, attrs=None, choices=()):
        from cc3.marketplace.models import Ad
        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        output = ['<ul>']
        # Normalize to strings
        str_values = set([force_text(v) for v in value])

        for i, (option_value, option_label) in enumerate(
                chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if id_:
                final_attrs = dict(final_attrs, id='{0}_{1}'.format(id_, i))
                label_for = format_html(' for="{0}_{1}"', id_, i)
            else:
                label_for = ''

            community_count = Ad.objects.filter(
                created_by__community=option_value, status=AD_STATUS_ACTIVE).count()
            output.append(self.render_checkbox(
                final_attrs, option_value,
                u"{0} ({1})".format(_(option_label), community_count),
                str_values, name, label_for))
        output.append('</ul>')

        return mark_safe('\n'.join(output))
