import datetime

from django.conf import settings
from django.utils.timezone import utc

from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions


#http://stackoverflow.com/questions/14567586/
# token-authentication-for-restful-api-should-the-token-be-periodically-changed
class FilesTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        utc_now = datetime.datetime.utcnow().replace(tzinfo=utc)

        if token.created < utc_now - datetime.timedelta(seconds=settings.FILES_TOKEN_AGE):
            raise exceptions.AuthenticationFailed('Token has expired')

        return token.user, token
