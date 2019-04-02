import logging

from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, views
from rest_framework.response import Response

from cc3.cyclos.models import User
from .models import UserCause

LOG = logging.getLogger(__name__)


class JoinCauseAPIView(views.APIView):
    """
    Given a specific user PK related to a charity organization, makes it
    the cause donations choice for the current request user.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, cause_pk, format=None):
        """
        Checks if the requested user is a charity organization. If so, makes it
        the cause donation choice for the request user. Otherwise, returns 404
        error.
        """
        cause = get_object_or_404(User, pk=int(cause_pk))

        good_cause_group = getattr(settings, 'CYCLOS_CHARITY_MEMBER_GROUP', '')
        if not good_cause_group:
            LOG.critical(u'Django setting CYCLOS_CHARITY_MEMBER_GROUP not'
                         u' defined.')
            return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

        if cause.cc3_profile.cyclos_group.name == good_cause_group:
            try:
                user_cause = UserCause.objects.get(consumer=request.user)
            except UserCause.DoesNotExist:
                user_cause = UserCause(consumer=request.user)

            user_cause.cause = cause
            user_cause.save()

            LOG.info(u'User {0} joined good cause {1}'.format(
                request.user, cause))

            return Response(status=status.HTTP_201_CREATED)

        return Response(
            u'Cause {0} not found'.format(cause_pk),
            status=status.HTTP_404_NOT_FOUND)
