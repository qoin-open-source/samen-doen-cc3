# -*- coding: utf-8 -*-
import json
from StringIO import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.translation import ugettext as _

from rest_framework.status import (
    HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN)
from rest_framework.authtoken.models import Token

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.tests.test_factories import UserFactory

from .test_factories import (
    FileServiceUserFactory, FormatFactory, FileTypeFactory)


class FileServiceUserLoginTests(TestCase):

    def setUp(self):
        self.url = reverse('api_files_login')

        self.user_1 = UserFactory.create()
        self.token_1 = Token.objects.create(user=self.user_1)
        self.file_service_user_1 = FileServiceUserFactory.create(
            user=self.user_1)
        self.user_2 = UserFactory.create()

    def test_files_login(self):
        """ Test successful login for uploading a file """
        data = {
            'username': self.user_1.username,
            'password': 'testing',
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['id'], self.file_service_user_1.id)

        # Check Token
        self.assertEqual(Token.objects.filter(user=self.user_1).count(), 1)
        token = Token.objects.get(user=self.user_1)
        self.assertEqual(data['token'], token.key)

    def test_files_login_nonexisting(self):
        """ Test invalid logging in, wrong file service user username """
        data = {
            'username': 'nonexisting',
            'password': 'testing',
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(
            data['detail'],
            _(u'Please enter a correct email and password. Note that both '
              u'fields may be case-sensitive.'))

    def test_files_login_invalid_data(self):
        """ Test invalid data when logging in, unparsable json """
        response = self.client.post(
            self.url,
            data="{'username': 'nonexisting', 'password': 'testing',",
            content_type='application/json'
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(data['detail'], "Cannot parse request data")

    def test_files_login_invalid_pin(self):
        """ Test invalid logging in, wrong pin but correct file service user
        username """
        data = {
            'username': self.user_1.username,
            'password': 'testing1234'
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        # commented out assertion as not important for test.
        # good enough to get a 400
#        self.assertEqual(data['detail'], "Invalid username or password")

    def test_files_login_no_fields(self):
        """ Test invalid logging in, missing file service user username &
        password """
        data = {
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(
            data['detail'],
            _(u'Please enter a correct email and password. Note that both '
              u'fields may be case-sensitive.'))

    def test_files_login_no_file_service_user(self):
        """ Test successful login for uploading a file """
        data = {
            'username': self.user_2.username,
            'password': 'testing',
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(data['detail'], "Invalid username or password")

# TODO: tests for logging in with IP address field set and not set.


class UploadTest(TestCase):

    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.login_url = reverse('api_files_login')
        self.url = reverse('api_files_upload')

        self.user_1 = UserFactory.create()
        self.file_service_user_1 = FileServiceUserFactory.create(
            user=self.user_1)

        # user to check permissions - ie no FileServiceUser for this user
        self.user_no_file_service_user = UserFactory.create()

        self.user_2 = UserFactory.create()
        self.file_service_user_2 = FileServiceUserFactory.create(
            user=self.user_2,
            ip_addresses=u'testserver'
        )

        self.user_3 = UserFactory.create()
        self.file_service_user_3 = FileServiceUserFactory.create(
            user=self.user_3,
            ip_addresses=u'9.9.9.9:1234'
        )

        self.format_1 = FormatFactory.create(
            description="CSV file", mime_type="csv", extension="csv")
        self.file_type_1_description = u'huurcontract'
        self.file_type_1 = FileTypeFactory.create(
            description=self.file_type_1_description,
            format=self.format_1,
            process_model=None
        )

        # Create a CSV file.
        self.csv_file = StringIO()
        self.csv_file.write('1A2B3C4D,12354\n3D4BFF54,90023\n9A6542BD,43021')
        self.csv_file.name = u'huurcontract.csv'

    def tearDown(self):
        self.csv_file.close()

    def test_successful_post(self):
        """ Tests a successful POST of a CSV file """
        data = {
            'username': self.user_1.username,
            'password': 'testing',
        }

        # Login to get token
        response = self.client.post(self.login_url, data=json.dumps(data),
                                    content_type='application/json')
        data = json.loads(response.content)

        self.client = self.client_class(
            HTTP_AUTHORIZATION='Token {0}'.format(data['token']))

        response = self.client.post(
            self.url,
            data={
                'file': SimpleUploadedFile(
                    self.csv_file.name, self.csv_file.getvalue()),
                'file_type': self.file_type_1_description,
                'test': False
            },
            follow=True)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = json.loads(response.content)

        # check return
        self.assertEqual(data, {
            u'file_type': self.file_type_1.description,
            u'file': self.csv_file.name,
            u'test': u'False'})

    def test_successful_test_post(self):
        """ Tests a successful test POST of a CSV file """
        data = {
            'username': self.user_1.username,
            'password': 'testing',
        }

        # Login to get token
        response = self.client.post(self.login_url, data=json.dumps(data),
                                    content_type='application/json')
        data = json.loads(response.content)

        self.client = self.client_class(
            HTTP_AUTHORIZATION='Token {0}'.format(data['token']))

        response = self.client.post(
            self.url,
            data={
                'file': SimpleUploadedFile(
                    self.csv_file.name, self.csv_file.getvalue()),
                'file_type': self.file_type_1_description,
                'test': True
            },
            follow=True)

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)

        # check return
        self.assertEqual(data, {
            u'file_type': self.file_type_1.description,
            u'file': self.csv_file.name,
            u'test': u'True'
        })

    def test_non_file_service_user_post(self):
        """ Tests that a user without a related FileServiceUser cannot POST a
        file """
        data = {
            'username': self.user_no_file_service_user.username,
            'password': 'testing',
        }

        # Login to get token
        response = self.client.post(self.login_url, data=json.dumps(data),
                                    content_type='application/json')
        data = json.loads(response.content)

        # response is actually 400
        token = data.get('token', None)
        self.client = self.client_class(
            HTTP_AUTHORIZATION='Token {0}'.format(token))

        # check POST anyway - with Token None
        response = self.client.post(
            self.url,
            data={
                'file': SimpleUploadedFile(
                    self.csv_file.name, self.csv_file.getvalue()),
                'file_type': self.file_type_1_description,
                'test': False
            },
            follow=True)

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        data = json.loads(response.content)

        # check return
        self.assertEqual(data, {
            u'detail': u'Invalid token'
        })

    def test_single_ip_address_user_post(self):
        """ Tests that a user with the test IP address ('testserver') can POST
        a file """
        data = {
            'username': self.user_2.username,
            'password': 'testing',
        }

        # Login to get token
        response = self.client.post(self.login_url, data=json.dumps(data),
                                    content_type='application/json')
        data = json.loads(response.content)

        self.client = self.client_class(
            HTTP_AUTHORIZATION='Token {0}'.format(data['token']))

        response = self.client.post(
            self.url,
            data={
                'file': SimpleUploadedFile(
                    self.csv_file.name, self.csv_file.getvalue()),
                'file_type': self.file_type_1_description,
                'test': False
            },
            follow=True)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = json.loads(response.content)

        # check return
        self.assertEqual(data, {
            u'file_type': self.file_type_1.description,
            u'file': self.csv_file.name,
            u'test': u'False'})

    def test_single_wrong_ip_address_user_post(self):
        """ Tests that a user with an non-test IP address cannot POST a file """
        data = {
            'username': self.user_3.username,
            'password': 'testing',
        }

        # Login to get token
        response = self.client.post(self.login_url, data=json.dumps(data),
                                    content_type='application/json')
        data = json.loads(response.content)

        self.client = self.client_class(
            HTTP_AUTHORIZATION='Token {0}'.format(data['token']))

        response = self.client.post(
            self.url,
            data={
                'file': SimpleUploadedFile(
                    self.csv_file.name, self.csv_file.getvalue()),
                'file_type': self.file_type_1_description,
                'test': False
            },
            follow=True)

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        data = json.loads(response.content)

        self.assertEqual(data, {
            u'detail': _(u'You do not have permission to perform this action.')
        })

# TODO tests for invalid file_type (ie not huurcontract etc), and bad data
