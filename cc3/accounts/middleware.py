from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from cc3.cyclos.models.account import log_user_status_change


class CyclosAccountMiddleware(object):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if view_func.func_name not in ['password_change', 'logout']:
            try:
                profile = request.user.cc3_profile
                if profile.must_reset_password:
                    messages.add_message(
                        request, messages.INFO,
                        _('You must change your password before you can '
                          'continue.'))
                    return HttpResponseRedirect(reverse('password_change'))
            except (AttributeError, ObjectDoesNotExist):
                pass  # carry on


# Middleware for passing the request object to the log_user_status_change()
# function which is a User model post_save() signal handler
class UserStatusChangeMiddleware(object):
    def process_view(self, request, view_func, view_args, view_kwargs):
        log_user_status_change.change_author = request.user
