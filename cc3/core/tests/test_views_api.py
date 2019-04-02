import json

from django.core.urlresolvers import reverse
from django.test import TestCase

from rest_framework.test import APIRequestFactory
from rest_framework.test import APIClient

from cc3.core.tests.test_factories import CategoryFactory
from cc3.core.models import Category
from cc3.cyclos.tests.test_factories import UserFactory


class OwnerManageCardViewTestCase(TestCase):

    def setUp(self):
        self.category_1 = CategoryFactory.create()
        self.category_2 = CategoryFactory.create(active=False)
        self.category_3 = CategoryFactory.create()
        self.category_4 = CategoryFactory.create()
        self.user = UserFactory.create(is_superuser=True)

#        self.oauth_application = OAuthApplication.objects.create(

#        )
        self.user_2 = UserFactory.create()
        self.factory = APIRequestFactory()
        self.url = reverse('api_categories')

    def test_categories_api_login_not_required(self):
        """Tests login not required for ``CategoriesListAPIView``"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        returned_categories = json.loads(response.content)
        categories = Category.objects.filter(active=True)
        self.assertEqual(categories.count(), len(returned_categories))

    def test_categories_api_super_user_login(self):
        """Tests super user login for ``CategoriesListAPIView`` returns all"""

        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get(self.url)

        self.assertEqual(response.status_code, 200)
        returned_categories = json.loads(response.content)
        categories = Category.objects.all()
        self.assertEqual(categories.count(), len(returned_categories))

    def test_categories_api_user_login(self):
        """Tests super user login for ``CategoriesListAPIView`` returns all"""
        client = APIClient()
        client.force_authenticate(user=self.user_2)
        response = client.get(self.url)

        self.assertEqual(response.status_code, 200)
        returned_categories = json.loads(response.content)
        categories = Category.objects.filter(active=True)
        self.assertEqual(categories.count(), len(returned_categories))

