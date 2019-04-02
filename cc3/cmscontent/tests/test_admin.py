from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

from cc3.cyclos.tests.test_factories import UserFactory

from ..models import NewsEntry


class NewsEntryAdminTestCase(TestCase):

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)

    def test_news_entry_save_auto_set_user(self):
        """
        Tests automatically setting up the user from the current request user
        when creating a new ``NewsEntry`` instance in admin.
        """
        post_data = {
            'title': 'Testing `NewsEntry` admin interface',
            'content': 'This is the content of the news.'
        }
        self.client.login(username=self.user.username, password='testing')

        self.client.post(
            reverse('admin:cmscontent_newsentry_add'), post_data)

        # Check the ``created_by`` field was automatically set after saving.
        news_entry = NewsEntry.objects.latest('pk')
        self.assertEqual(news_entry.created_by, self.user)
