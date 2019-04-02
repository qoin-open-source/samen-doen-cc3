"""
Combination of two snippets which provides audit log functionality.

Log entry admin snippet (slightly modified to work)
Provides LogEntryAdmin for integration into Django admin
https://djangosnippets.org/snippets/2484/

Admin log entries management utils snippet
Provides CBV LogMixin (log_addition, log_change, log_deletion)
Modified to also provide log_user_action (which uses an additional
LogEntry.action_flag entry)

https://djangosnippets.org/snippets/2539/

"""

import logging

from django.contrib import admin
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.utils.html import escape
from django.core.urlresolvers import reverse, NoReverseMatch
from django.contrib.admin import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.utils.text import get_text_list
from django.core.exceptions import ObjectDoesNotExist

FLAG_USER_ACTION = 4

logger = logging.getLogger(__name__)


class LogEntryAdmin(admin.ModelAdmin):

    date_hierarchy = 'action_time'

    readonly_fields = LogEntry._meta.get_all_field_names()

    list_filter = [
        'content_type', 'user',
    ]

    search_fields = [
        'user__username',
        'object_repr',
        'change_message'
    ]

    list_display = [
        'action_time',
        'user',
        'content_type',
        'object_link',
        'object_id',
        'get_action_flag',
        'get_change_message',
    ]

    def get_action_flag(self, obj):
        if obj.action_flag == ADDITION:
            return _("Created")
        if obj.action_flag == CHANGE:
            return _("Modified")
        if obj.action_flag == DELETION:
            return _("Deleted")
        if obj.action_flag == FLAG_USER_ACTION:
            return _("Action")
        return ""
    get_action_flag.short_description = _('Action')

    def get_change_message(self, obj):
        return obj.change_message
    get_change_message.short_description = _('Message')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return (request.user.is_superuser or request.user.has_perm(
            'admin.change_logentry')) and request.method != 'POST'

    def has_delete_permission(self, request, obj=None):
        return False

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            try:
                url = reverse('admin:{0}_{1}_change'.format(
                    ct.app_label, ct.model), args=[obj.object_id])
                link = u'<a href="{0}">{1}</a>'.format(
                    url, escape(obj.object_repr))
            except NoReverseMatch:
                link = escape(obj.object_repr)

        return link
    object_link.allow_tags = True
    object_link.admin_order_field = 'object_repr'
    object_link.short_description = u'object'

    def queryset(self, request):
        return super(LogEntryAdmin, self).queryset(
            request).prefetch_related('content_type')


def get_change_message(fields):
    """
    Create a change message for *fields* (a sequence of field names).
    """
    return _('Changed %s.') % get_text_list(fields, _('and'))

admin.site.register(LogEntry, LogEntryAdmin)


def addition(request, obj, message=''):
    """
    Log that an object has been successfully added.
    """
    models.LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=force_unicode(obj),
        action_flag=models.ADDITION,
        change_message=message
    )


def change(request, obj, message_or_fields):
    """
    Log that an object has been successfully changed.

    The argument *message_or_fields* must be a sequence of modified field names
    or a custom change message.
    """
    if isinstance(message_or_fields, basestring):
        message = message_or_fields
    else:
        message = get_change_message(message_or_fields)
    models.LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=force_unicode(obj),
        action_flag=models.CHANGE,
        change_message=message
    )


def deletion(request, obj, object_repr=None):
    """
    Log that an object will be deleted.
    """
    models.LogEntry.objects.log_action(
        user_id=request.user.id,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=object_repr or force_unicode(obj),
        action_flag=models.DELETION
    )


class Diff:
    def __init__(self, model):
        self.state = {}

        for field in model._meta.get_all_field_names():

            try:
                self.state[field] = getattr(model, field)
            except AttributeError:
                # Many to many relations are ignored
                # since they are not editable in the
                # profile page
                pass
            except ObjectDoesNotExist:
                # Related fields left empty are assumend
                # to be empty
                pass

    def diff(self, model):
        """
        Produces a dictionary with the fields that have different
        values for two models.

        returns {field_name => (old_value, new_value)}

        """
        diff = {}

        for k, v in self.state.iteritems():
            try:

                if v != getattr(model, k):
                    diff[k] = (v, getattr(model, k))

            except AttributeError:
                diff[k] = (v, None)
            except model.DoesNotExist:
                diff[k] = (v, None)

        return diff

    def diff_fields(self, model):

        return self.diff(model).keys()

    def log_if_changed(self, request, model):

        changed_fields = self.diff_fields(model)

        if len(changed_fields) > 0:
            change(
                request,
                model,
                changed_fields
            )


def user_action(request, obj, message):
    """
    Log a generic action done by a user, useful for when add/change/delete
    aren't appropriate.
    """

    content_type_id = ContentType.objects.get_for_model(obj).pk
    object_id = obj.pk
    object_repr = force_unicode(obj)

    models.LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=content_type_id,
        object_id=object_id,
        object_repr=object_repr,
        action_flag=FLAG_USER_ACTION,
        change_message=message)


def in_bulk(request, added, changed, deleted):
    """
    Log all *added*, *changed* and *deleted* instances.

    Note that, while *added* and *deleted* are sequences of instances,
    *changed* must be a sequence of tuples *(instance, message_or_fields)*,
    where *message_or_fields* is a sequence of modified field names
    or a custom change message.
    """
    for instance in added:
        addition(request, instance)
    for instance, fields in changed:
        if fields:
            change(request, instance, fields)
    for instance in deleted:
        deletion(request, instance)


class LogMixin(object):
    """
    Class based views mixin that adds simple wrappers to
    the three functions above.
    """
    def __init__(self):
        self.request = None

    def log_addition(self, instance, message=''):
        """
        Log that an object has been successfully added.
        """
        addition(self.request, instance, message)

    def log_change(self, instance, message_or_fields):
        """
        Log that an object has been successfully changed.
        """
        change(self.request, instance, message_or_fields)

    def log_deletion(self, instance, instance_repr=None):
        """
        Log that an object will be deleted.
        """
        deletion(self.request, instance, instance_repr)

    def log_user_action(self, instance, message):
        """
        Log that the current user has done something interesting.
        """
        user_action(self.request, instance, message)

    def logall(self, added, changed, deleted):
        in_bulk(self.request, added, changed, deleted)


class AdminLogger(LogMixin):
    """
    A more generic Python object that can be used as a logger
    taking the request in the constructor.
    """
    def __init__(self, request):
        super(AdminLogger, self).__init__()
        self.request = request


class AdminLogCollector(object):
    """
    A class to collect logs that will be reported later.

    It can be useful, for example, when you need to add log entries
    in forms (e.g. in a custom admin page) without the need to pass a
    request argument::

        class MyForm(forms.Form):
            def __init__(self, *args, **kwargs):
                super(MyForm, self).__init__(*args, **kwargs)
                self.collector = AdminLogCollector()

            def save(self):
                ... add some instance
                self.collector.added(instance)

    If you have a formset of forms like the above, it is easy to
    collect all logs::

        class MyBaseFormSet(BaseFormSet):
            def save(self):
                collectors = []
                for form in self.forms:
                    form.save()
                    collectors.append(form.collector)
                # collect changes for all forms
                self.collector = sum(collectors, AdminLogCollector())
                # return the number of forms that did something
                return len(filter(None, collectors))

    In the view you can actually save all collected log entries::

        formset.collector.logall(request)
    """
    def __init__(self, added=None, changed=None, deleted=None, _logger=None):
        self._added = set() if added is None else set(added)
        self._changed = set() if changed is None else set(changed)
        self._deleted = set() if deleted is None else set(deleted)
        self._logger = _logger or in_bulk
        self._done = False

    def __add__(self, other):
        added, changed, deleted = other.get_collected()
        return self.__class__(
            self._added.union(added),
            self._changed.union(changed),
            self._deleted.union(deleted),
            logger=self._logger
        )

    def __repr__(self):
        return repr(self.get_collected())

    def __nonzero__(self):
        return any(self.get_collected())

    def added(self, instance):
        """
        Collect an addition log.
        """
        self._added.add(instance)

    def changed(self, instance, message_or_fields):
        """
        Collect a change log.
        """
        if not isinstance(message_or_fields, basestring):
            message_or_fields = tuple(message_or_fields)
        self._changed.add((instance, message_or_fields))

    def deleted(self, instance):
        """
        Collect a deletion log.
        """
        self._deleted.add(instance)

    def get_collected(self):
        """
        Return a tuple *(additions, changes, deletions)*
        representing all the collected logs.
        """
        return self._added, self._changed, self._deleted

    def logall(self, request, redo=False):
        """
        Actually save all log entries using the given *request*.
        """
        if redo or not self._done:
            self._logger(request, self._added, self._changed, self._deleted)
            self._done = True
