from django.contrib.admin.templatetags.admin_static import static
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.urlresolvers import reverse
from django.forms.widgets import CheckboxSelectMultiple, CheckboxInput
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from cc3.cyclos.models import BusinessUserProxyModel, CardMachineUserProxyModel
from cc3.cyclos.models.account import CardUserProxyModel, FulfillmentProfileProxyModel


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
        return u'<div class="element checkbox-container checkbox"><label{0}>' \
               u'{1} {2}</label>{3}<span class="clearfix"></span>' \
               u'</div>'.format(label_for, rendered_cb, option_label,
                                post_label)


class BusinessUserForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    """
    Overrides ``django.contrib.admin.widgets.ForeignKeyRawIdWidget`` to provide
    a ``raw_id_fields`` option in admin interface classes for those places
    where a user filtering by 'is business' is needed.

    The widget actually will show a list of ``cyclos.User``s filtered to those
    who are 'business' users.
    """
    def render(self, name, value, attrs=None):
        """
        Overrides the base ``render`` method to use only the specific proxy
        model which filters ``cyclos.User``s by 'business'.
        """
        rel_to = BusinessUserProxyModel
        if attrs is None:
            attrs = {}
        extra = []

        if rel_to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            related_url = reverse(
                'admin:{0}_{1}_changelist'.format(
                    rel_to._meta.app_label, rel_to._meta.model_name),
                current_app=self.admin_site.name)

            params = self.url_parameters()
            if params:
                url = '?' + '&amp;'.join(
                    ['{0}={1}'.format(k, v) for k, v in params.items()])
            else:
                url = ''
            if "class" not in attrs:
                attrs['class'] = 'vForeignKeyRawIdAdminField'
            extra.append(
                '<a href="{0}{1}" class="related-lookup" id="lookup_id_{2}" '
                'onclick="return showRelatedObjectLookupPopup(this);"> '
                ''.format(related_url, url, name))
            extra.append('<img src="{0}" width="16" height="16" alt="{1}" />'
                         '</a>'.format(
                             static('admin/img/selector-search.gif'),
                             _('Lookup')))
        output = [super(ForeignKeyRawIdWidget, self).render(
            name, value, attrs)] + extra
        if value:
            output.append(self.label_for_value(value))
        return mark_safe(''.join(output))


class CardMachineUserForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    """
    Overrides ``django.contrib.admin.widgets.ForeignKeyRawIdWidget`` to provide
    a ``raw_id_fields`` option in admin interface classes for those places
    where a user filtering by particular user types is needed.

    The widget actually will show a list of ``cyclos.User``s filtered to those
    who are in CYCLOS_CARD_MACHINE_MEMBER_GROUPS settings defined groups of
    users.
    """
    rel_to = CardMachineUserProxyModel

    def render(self, name, value, attrs=None):
        """
        Overrides the base ``render`` method to use only the specific proxy
        model which filters ``cyclos.User``s by 'business'.
        """
        rel_to = self.rel_to
        if attrs is None:
            attrs = {}
        extra = []

        if rel_to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            related_url = reverse(
                'admin:{0}_{1}_changelist'.format(
                    rel_to._meta.app_label, rel_to._meta.model_name),
                current_app=self.admin_site.name)

            params = self.url_parameters()
            if params:
                url = '?' + '&amp;'.join(
                    ['{0}={1}'.format(k, v) for k, v in params.items()])
            else:
                url = ''
            if "class" not in attrs:
                attrs['class'] = 'vForeignKeyRawIdAdminField'
            extra.append(
                '<a href="{0}{1}" class="related-lookup" id="lookup_id_{2}" '
                'onclick="return showRelatedObjectLookupPopup(this);"> '
                ''.format(related_url, url, name))
            extra.append('<img src="{0}" width="16" height="16" alt="{1}" />'
                         '</a>'.format(
                             static('admin/img/selector-search.gif'),
                             _('Lookup')))
        output = [super(ForeignKeyRawIdWidget, self).render(
            name, value, attrs)] + extra
        if value:
            output.append(self.label_for_value(value))
        return mark_safe(''.join(output))


class CardUserForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    """
    Overrides ``django.contrib.admin.widgets.ForeignKeyRawIdWidget`` to provide
    a ``raw_id_fields`` option in admin interface classes for those places
    where a user filtering by particular user types is needed.

    The widget actually will show a list of ``cyclos.User``s filtered to those
    who are in CYCLOS_CARD_MACHINE_MEMBER_GROUPS settings defined groups of
    users.
    """
    rel_to = CardUserProxyModel

    def render(self, name, value, attrs=None):
        """
        Overrides the base ``render`` method to use only the specific proxy
        model which filters ``cyclos.User``s by 'business'.
        """
        rel_to = self.rel_to
        if attrs is None:
            attrs = {}
        extra = []

        if rel_to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            related_url = reverse(
                'admin:{0}_{1}_changelist'.format(
                    rel_to._meta.app_label, rel_to._meta.model_name),
                current_app=self.admin_site.name)

            params = self.url_parameters()
            if params:
                url = '?' + '&amp;'.join(
                    ['{0}={1}'.format(k, v) for k, v in params.items()])
            else:
                url = ''
            if "class" not in attrs:
                attrs['class'] = 'vForeignKeyRawIdAdminField'
            extra.append(
                '<a href="{0}{1}" class="related-lookup" id="lookup_id_{2}" '
                'onclick="return showRelatedObjectLookupPopup(this);"> '
                ''.format(related_url, url, name))
            extra.append('<img src="{0}" width="16" height="16" alt="{1}" />'
                         '</a>'.format(
                             static('admin/img/selector-search.gif'),
                             _('Lookup')))
        output = [super(ForeignKeyRawIdWidget, self).render(
            name, value, attrs)] + extra
        if value:
            output.append(self.label_for_value(value))
        return mark_safe(''.join(output))

#from cc3.cyclos.models.account import FulfillmentProfileProxyModel


class FulfillmentProfileForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    rel_to = FulfillmentProfileProxyModel

    def render(self, name, value, attrs=None):
        """
        Overrides the base ``render`` method to use only the specific proxy
        model which filters ``cyclos.User``s by 'business'.
        """
        rel_to = self.rel_to
        if attrs is None:
            attrs = {}
        extra = []

        if rel_to in self.admin_site._registry:
            # The related object is registered with the same AdminSite
            hello = 'admin:{0}_{1}_changelist'.format(
                rel_to._meta.app_label, rel_to._meta.model_name)
            related_url = reverse(hello,
                current_app=self.admin_site.name)

            params = self.url_parameters()
            if params:
                url = '?' + '&amp;'.join(
                    ['{0}={1}'.format(k, v) for k, v in params.items()])
            else:
                url = ''
            if "class" not in attrs:
                attrs['class'] = 'vForeignKeyRawIdAdminField'
            extra.append(
                '<a href="{0}{1}" class="related-lookup" id="lookup_id_{2}" '
                'onclick="return showRelatedObjectLookupPopup(this);"> '
                ''.format(related_url, url, name))
            extra.append('<img src="{0}" width="16" height="16" alt="{1}" />'
                         '</a>'.format(
                static('admin/img/selector-search.gif'),
                _('Lookup')))
        output = [super(ForeignKeyRawIdWidget, self).render(
            name, value, attrs)] + extra
        if value:
            output.append(self.label_for_value(value))
        return mark_safe(''.join(output))

