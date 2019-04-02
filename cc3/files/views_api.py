import datetime

import logging

from django.contrib.auth import authenticate
from django.forms import ValidationError
from django.utils.timezone import utc

from rest_framework import status, views, parsers
from rest_framework.response import Response

from rest_framework.authtoken.models import Token
from rest_framework.parsers import ParseError

from cc3.core.api.permissions import IsFilesServiceUser

from .authentication import FilesTokenAuthentication
from .forms import FileTypeSetForm
from .models import FileServiceUser, FileTypeSet
from .serializers import UploadSerializer


"""
Available resources:

/api/v1/files/login/
/api/v1/files/upload/

"""

LOG = logging.getLogger(__name__)


class FileServiceUserLoginView(views.APIView):
    """
    POST-only, Authenticate

    Given the username and password of a file service user,
    authenticate and the FileServiceUserPermissions (IP address if necessary).

    If valid, return a HTTP 200 OK and return the fileserviceuser ID and a token
    for using the other resources.

    If not valid, return a HTTP 400 Bad Request response with the message:
    - "Invalid username or password", if not found / bad ip address.

    Example POST data:

    {
      "username": "file_service_user"
      "password": "testing"
    }

    {{{
        $ curl -H "Content-Type: application/json" -d
            '{"username":"user","password":"password"}'
            http://localhost:8000/api/v1/files/login/

        returns:
             {"token": "b7fc923b2ee3bb2a2a935f1c72e1b9df21ef389b", "id": 1}
    }}}
    """
    permission_classes = ()

    def post(self, request):
        LOG.info(u'Files login')

        try:
            msg = u'Invalid username or password'
            # TODO protect raw data through form validation?
            user = authenticate(username=request.data.get('username', ''),
                                password=request.data.get('password', ''))
            if not user:
                LOG.info(msg)
                return Response({'detail': msg},
                                status=status.HTTP_400_BAD_REQUEST)
        except ParseError:
            return Response({'detail': u"Cannot parse request data"},
                            status=status.HTTP_400_BAD_REQUEST)
        except ValidationError, e:
            return Response({'detail': ''.join(e.messages)},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            file_service_user = FileServiceUser.objects.get(user=user)
        except FileServiceUser.DoesNotExist:
            LOG.info(msg)
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)

        # Terminal has been found, create a Token for it
        (token, created) = Token.objects.get_or_create(user=user)
        if created:
            LOG.info(u'Created token: {0}'.format(user.id))
        else:
            LOG.info(u'Reusing token: {0}'.format(user.id))
            # update the created time of the token to keep it valid
            token.created = datetime.datetime.utcnow().replace(tzinfo=utc)
            token.save()

        return Response({'token': token.key, 'id': file_service_user.id})


class UploadFileView(views.APIView):
    """
    POST-only, Token authentication required

    Given a file_type description (ie huurcontract) and file, validate and if
    not testing, save data to associated (temp) model.

    If valid, return a HTTP 200 OK (if testing) or HTTP_201_CREATED
    (if uploading) and return the serialized data.

    If not valid return a HTTP 400 Bad Request response with the message:
    "Invalid".

    Example POST data:

    DATA: {'file_type': 'huurcontract', 'test': True} # test = True, only test,
    test = False or None, full upload
    FILES: {'file', doc}


     2. POST a file to the upload url

      - Add an Authorization Http header with the token
     {{{
     Authorization: Token b7fc923b2ee3bb2a2a935f1c72e1b9df21ef389b
     }}}

      - post the file

     {{{
     $ curl -H "Authorization: Token b7fc923b2ee3bb2a2a935f1c72e1b9df21ef389b"
     -F file=@/var/local/test.rtf -F file_type=huurcontract
     -F test=True http://localhost:8000/api/v1/files/upload/

     returns

     {"file_type": "huurcontract", "file": "test.rtf", "test": "True"}
     }}}

    """
    authentication_classes = (FilesTokenAuthentication,)
    parser_classes = (parsers.MultiPartParser,)
    permission_classes = (IsFilesServiceUser, )

    def post(self, request):
        """
        Creates a new ``Upload``, recording type of file,
        date and user creating it
        """
        LOG.info(u'Received upload POST from user {0}'.format(
            self.request.user))
        request.data['user_created'] = self.request.user.pk
        serializer = UploadSerializer(data=request.data)

        if serializer.is_valid():
            # only save the file if not in test mode
            return_dict = serializer.data
            test_mode = request.data.get('test', None)
            return_dict['test'] = test_mode
            # don't return user_created from web service
            return_dict.pop('user_created')
            # DRF3 doesnt' appear to return the filename as DRF2 did
            return_dict['file'] = request.data['file'].name

            if test_mode == u"True":
                return Response(return_dict, status=status.HTTP_200_OK)
            else:
                serializer.save()
                return Response(return_dict, status=status.HTTP_201_CREATED)
        else:
            LOG.debug(serializer.errors)

            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProcessFileTypeSetView(views.APIView):
    """
    POST-only, Token authentication required

    Given a file_type_set name (ie stadlander), run associated rule set for each
    instance of data for file_types. List of instances, linked by the
    'identifier field'...

    If valid, return a HTTP 200 OK (if testing) or HTTP_201_CREATED
    (if uploading) and return the serialized data.

    If not valid return a HTTP 400 Bad Request response with the message:
    "Invalid".

    Example POST data:

    DATA: {'name': 'stadlander'}
    """
    authentication_classes = (FilesTokenAuthentication,)
    permission_classes = (IsFilesServiceUser, )

    def post(self, request):

        # TODO protect raw data through form validation?
        form = FileTypeSetForm(data=request.data)
        if form.is_valid():
            filetypeset = FileTypeSet.objects.get(
                name=form.cleaned_data['name'])
            filetypeset.run_ruleset()

            return_dict = {}
            return Response(return_dict, status=status.HTTP_200_OK)
        else:
            return Response(
                form.errors, status=status.HTTP_400_BAD_REQUEST)
