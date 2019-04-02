from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings

from mock import patch, PropertyMock

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.tests.test_factories import CC3ProfileFactory

from ..models import UserCause


class JoinCauseAPIViewTestCase(TestCase):
    """
    Test case for the ``JoinCauseAPIView`` view.
    """
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.user = CC3ProfileFactory.create()
        self.cause = CC3ProfileFactory.create()

        self.url = reverse(
            'api_rewards_causes_join', kwargs={'cause_pk': self.cause.user.pk})

    def test_join_cause_endpoint_login_required(self):
        """
        Tests login required to access the API endpoint.
        """
        response = self.client.get(self.url)

        # was 403 - but need to use token auth for another area of the system
        # and introducing djoser updates the status code to 401:
        # - HTTP Error 401 Unauthorized
        self.assertEqual(response.status_code, 401)

    def test_join_cause_does_not_exist(self):
        """
        Tests the API endpoint when the requested cause does not exist (or the
        ``User`` object does not belong to a charity organization).
        """
        self.client.login(username=self.user.user.username, password='testing')
        response = self.client.get(
            reverse('api_rewards_causes_join', kwargs={'cause_pk': '9999'}),
            follow=True)

        self.assertEqual(response.status_code, 404)

    @patch('cc3.cyclos.models.CC3Profile.cyclos_group')
    def test_join_cause_success(self, mock):
        """
        Tests a successful GET request over the API endpoint.

        Mocks the ``CC3Profile.cyclos_group`` model property, so it can return
        the proper expected successful value without hitting the Cyclos
        backend.
        """
        type(mock).name = PropertyMock(
            return_value=settings.CYCLOS_CHARITY_MEMBER_GROUP)

        self.client.login(username=self.user.user.username, password='testing')
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.status_code, 201)

        # Check that the selection was done.
        user_cause = UserCause.objects.latest('pk')

        self.assertEqual(user_cause.cause, self.cause.user)
        self.assertEqual(user_cause.consumer, self.user.user)

    @patch('cc3.cyclos.models.CC3Profile.cyclos_group')
    def test_join_cause_wrong_group(self, mock):
        """
        Tests failure when the supposed cause CC3 profile belongs to the wrong
        Cyclos group.
        """
        type(mock).id = PropertyMock(
            return_value=999)

        self.client.login(username=self.user.user.username, password='testing')
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.status_code, 404)

    @override_settings(CYCLOS_CHARITY_MEMBER_GROUP=None)
    def test_join_cause_no_settings_defined(self):
        """
        Tests failure when there are no Django settings defined.
        """
        del settings.CYCLOS_CHARITY_MEMBER_GROUP

        self.client.login(username=self.user.user.username, password='testing')
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.status_code, 501)
