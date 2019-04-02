import logging

from rest_framework import permissions

from cc3.cyclos.models import CC3Profile
from cc3.files.models import FileServiceUser

LOG = logging.getLogger(__name__)


class IsCommunityAdmin(permissions.BasePermission):
    """
    Allows only access to Community administrators.
    """
    def has_permission(self, request, view):
        user = request.user if request.user.is_authenticated() else None

        return True if user and user.get_admin_community() else False


class IsAdManager(permissions.IsAuthenticated):
    """
    Allows only access to the users who can manage this specific Ad.

    You can specify safe methods at class level, so for example you can allow
    all users GET the existing images, but only owners of the ad will be able
    to POST a new one.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.can_edit(request.user)


class IsFilesServiceUser(permissions.IsAuthenticated):
    """
    Allows access to users with a FileServiceUser instance
    """
    def has_permission(self, request, view):
        user = request.user if request.user.is_authenticated() else None

        try:
            file_service_user = FileServiceUser.objects.get(user=user)

        except FileServiceUser.DoesNotExist:
            file_service_user = None

        host = request.get_host()
        # returns PEP 3333 formatted host - ie 127.0.0.1:8000
        # NB with django test server, this returns 'testserver'

        LOG.info(u'IsFilesServiceUser: host = {0}'.format(host))
        ip_address = request.get_host()

        return True if file_service_user and \
                       file_service_user.check_ip_address(ip_address) else False


class HasCompletedProfile(permissions.BasePermission):
    """
    Allows access only to users with complete profiles.
    """
    def has_permission(self, request, view):
        user = request.user if request.user.is_authenticated() else None
        return (
            CC3Profile.viewable.has_completed_profile(request.user)
            if user else False
        )


class IsSuperuserOrReadOnly(permissions.BasePermission):
    """
    Allow superusers to edit details otherwise read only.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.is_superuser
