import logging

from django import forms
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.mail import mail_admins
from django.utils.translation import ugettext as _

from cc3.cyclos.models import User

LOG = logging.getLogger(__name__)


class EmailOrUsernameModelBackend(object):

    def authenticate(self, username=None, password=None):

        """
        Authenticate a user with either email or username.

        :param username: Used to compare with either ``email`` or ``username``
        field of ``User``.
        :param password: Users password.
        :return: User instance or ``None``.
        """
        if '@' in username:
            kwargs = {'email': username}
        else:
            kwargs = {'username': username}
        error = _(u'Please enter a correct email and password. Note that '
                  u'both fields may be case-sensitive.')
        try:
            user = User.objects.get(**kwargs)
            if user.check_password(password):
                return user
            else:
                raise forms.ValidationError(error)
        except User.DoesNotExist:
            login_type = getattr(settings, "LOGIN_TYPES", "EMAIL")
            # if system only allows login with email (only)
            if login_type == "EMAIL":
                raise forms.ValidationError(error)
            elif login_type == "EMAIL_OR_USERNAME":
                raise forms.ValidationError(error)
            return None  # FIXME: This code will never be reached - it always will fall in any of two conditionals above. Please remove it if proceeds.
        except MultipleObjectsReturned:
            # Database inconsistency - only 1 user is possible.
            message = u"Multiple objects returned when trying to " \
                      u"authenticate user '{0}'. A database consistency " \
                      u"check must be manually performed.".format(username)
            # Log the issue in server logs.
            LOG.critical(message)

            # Send an email to the admins with the information if proceeds.
            if not settings.DEBUG:
                mail_admins(
                    u'Database inconsistency', message, fail_silently=True)

            # Return a nice ``None`` to avoid provoking a 500 error.
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
