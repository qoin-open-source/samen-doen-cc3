from datetime import timedelta
from StringIO import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from cc3.cards.models import Card
from cc3.cyclos.tests.test_factories import UserFactory

from .test_factories import CardFactory, OperatorFactory, TerminalFactory
from ..models import CardNumber, Operator, Terminal
from ..views import NFCTerminalsListView, OwnerManageCardView

from django.utils.translation import ugettext_lazy as _

class OwnerManageCardViewTestCase(TestCase):

    def setUp(self):
        self.user = UserFactory.create()

        now = timezone.now()

        self.card_1 = CardFactory.create(
            owner=self.user, creation_date=now - timedelta(days=1))
        self.card_2 = CardFactory.create(
            owner=self.user, creation_date=now - timedelta(days=2))
        self.card_3 = CardFactory.create(
            owner=self.user, creation_date=now - timedelta(days=3))

        self.factory = RequestFactory()
        self.url = reverse('owner_manage_card')

    def test_owner_manage_card_login_required(self):
        """Tests login required for ``OwnerManageCardView``"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '{0}?next={1}'.format(reverse('auth_login'), self.url))

    def test_owner_manage_card_get_context_data(self):
        """Tests the ``get_context_data`` method of ``OwnerManageCardView``"""
        request = self.factory.get(self.url)
        request.user = self.user

        view = OwnerManageCardView()
        view.request = request

        context = view.get_context_data()

        card_list = Card.objects.filter(
            owner=self.user).order_by('-creation_date')

        self.assertQuerysetEqual(
            context['owners_cards'],
            map(repr, card_list)
        )


class NFCTerminalsListViewTestCase(TestCase):

    def setUp(self):
        self.terminal_1 = TerminalFactory.create()
        self.terminal_2 = TerminalFactory.create()
        self.terminal_3 = TerminalFactory.create()

        self.operator_1 = OperatorFactory.create(
            business=self.terminal_1.business)
        self.operator_2 = OperatorFactory.create(
            business=self.terminal_1.business)
        self.operator_3 = OperatorFactory.create(
            business=self.terminal_1.business)

        self.factory = RequestFactory()
        self.url = reverse('terminals_list')

    def test_terminals_list_login_required(self):
        """Tests login required for 'business terminals list' view"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '{0}?next={1}'.format(reverse('auth_login'), self.url))

    def test_terminals_list_get_queryset(self):
        """Tests the ``get_queryset`` method to ensure that the view only
        returns ``Terminal`` objects related to the current business"""

        self.client.login(
            username=self.operator_1.business.username, password='testing')

        response = self.client.get(self.url)
        self.assertQuerysetEqual(
            list(response.context['object_list']),
            ["{0}".format(repr(t)) for t in Terminal.objects.filter(
                business=self.terminal_1.business)])

    def test_terminals_list_get_context_data(self):
        """Tests the ``get_context_data`` method to ensure that the operators
        list is being passed to the template"""
        self.client.login(
            username=self.operator_1.business.username, password='testing')

        response = self.client.get(self.url)

        self.assertQuerysetEqual(
            list(response.context['operators']),
            ["{0}".format(repr(t)) for t in Operator.objects.filter(
                business=self.terminal_1.business)])


class OperatorsCreateViewTestCase(TestCase):

    def setUp(self):
        self.operator_1 = OperatorFactory.create()
        self.operator_2 = OperatorFactory.create()
        self.operator_3 = OperatorFactory.create()
        self.url = reverse('operator_create')

    def test_operators_create_login_required(self):
        """Tests login required for 'terminal operators create' view"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '{0}?next={1}'.format(reverse('auth_login'), self.url))

    def test_operators_create_successful_post(self):
        """Tests a sucessful POST operation"""
        self.client.login(
            username=self.operator_1.business.username, password='testing')
        response = self.client.post(
            self.url, data={'name': 'john_doe', 'business': self.operator_1.business.id, 'pin': '1234'}, follow=True)

        self.assertRedirects(response, reverse('terminals_list'))
        self.assertEqual(response.status_code, 200)

        # Check the new ``Operator`` object.
        operator = Operator.objects.latest('pk')

        self.assertEqual(operator.name, 'john_doe')
        self.assertEqual(operator.pin, '1234')
        self.assertEqual(operator.business, self.operator_1.business)

    def test_operators_create_unique_fail_post(self):
        '''Test that operator user names are unique for a given business.'''
        self.client.login(
            username=self.operator_1.business.username, password='testing')

        response = self.client.post(
            self.url, data={'name': self.operator_1.name, 'business': self.operator_1.business.id, 'pin': '1234'}, follow=True)

        self.assertContains(response=response, text=_("The user name is already in use. Please provide a unique user name."), status_code=200)

        qs = Operator.objects.filter(name=self.operator_1.name)
        self.assertEquals(1, qs.count())

    def test_operators_create_tampered_business_post(self):
        '''Test that operator user business cannot be tampered with.'''
        username = 'qpoubhjsdb'
        self.client.login(
            username=self.operator_1.business.username, password='testing')

        # assert that the two business users used for the test are different
        self.assertNotEqual(self.operator_1.business.id, self.operator_2.business.id)

        # assert that an operator with the specified user name doesn't already exist
        qs = Operator.objects.filter(name=username)
        self.assertEqual(qs.count(), 0)

        # attempt to create a new operator with a business id different that that of the logged in user
        response = self.client.post(
            self.url, data={'name': username, 'business': self.operator_2.business.id, 'pin': '1234'},
            follow=True)

        # assert that the post resulted in the creation of a new operator with the specified name
        qs = Operator.objects.filter(name=username)
        self.assertEqual(qs.count(), 1)

        john_doe = None
        if qs.count() == 1:
            john_doe = qs[0]

        # assert that business id of the newly created operator is the same as that of the logged in user
        self.assertEquals(john_doe.business.id, self.operator_1.business.id)


class OperatorsUpdateViewTestCase(TestCase):

    def setUp(self):
        self.operator_1 = OperatorFactory.create()
        self.operator_2 = OperatorFactory.create()

    def test_operators_update_login_required(self):
        """Tests login required for 'terminal operator update' view"""
        response = self.client.get(
            reverse('operator_update', kwargs={'pk': self.operator_1.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '{0}?next={1}'.format(
                reverse('auth_login'),
                reverse('operator_update', kwargs={'pk': self.operator_1.pk})))

    def test_operators_update_successful_post(self):
        """Tests a sucessful POST operation"""
        self.client.login(
            username=self.operator_1.business.username, password='testing')
        response = self.client.post(
            reverse('operator_update', kwargs={'pk': self.operator_1.pk}),
            data={'name': 'john_doe', 'business': self.operator_1.business.id, 'pin': '1234'}, follow=True)

        self.assertRedirects(response, reverse('terminals_list'))
        self.assertEqual(response.status_code, 200)

        # Check the updated ``Operator`` object.
        operator = Operator.objects.get(pk=self.operator_1.pk)

        self.assertEqual(operator.name, 'john_doe')
        self.assertEqual(operator.pin, '1234')
        self.assertEqual(operator.business, self.operator_1.business)

    def test_operators_update_tamper_business(self):
        """Tests that the business field received from the client is discarded"""
        self.client.login(
            username=self.operator_1.business.username, password='testing')

        # Make sure that the two operators have different values for their business field
        self.assertNotEquals(self.operator_1.business, self.operator_2.business)

        response = self.client.post(
            reverse('operator_update', kwargs={'pk': self.operator_1.pk}),
            data={'name': 'john_doe', 'business': self.operator_2.business.id, 'pin': '1234'}, follow=True)

        self.assertRedirects(response, reverse('terminals_list'))
        self.assertEqual(response.status_code, 200)

        # Check the updated ``Operator`` object.
        operator = Operator.objects.get(pk=self.operator_1.pk)

        self.assertEqual(operator.name, 'john_doe')
        self.assertEqual(operator.pin, '1234')
        self.assertEqual(operator.business, self.operator_1.business)


class OperatorsDeleteViewTestCase(TestCase):

    def setUp(self):
        self.operator_1 = OperatorFactory.create()

    def test_operator_delete_login_required(self):
        """Tests login required for 'terminal operator delete' view"""
        response = self.client.get(
            reverse('operator_delete', kwargs={'pk': self.operator_1.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, '{0}?next={1}'.format(
                reverse('auth_login'),
                reverse('operator_delete', kwargs={'pk': self.operator_1.pk})))

    def test_operator_delete_successful_post(self):
        """Tests a successful POST operation"""
        self.client.login(
            username=self.operator_1.business.username, password='testing')
        response = self.client.post(
            reverse('operator_delete', kwargs={'pk': self.operator_1.pk}),
            follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('terminals_list'))

        # Check the deleted ``Operator`` object.
        self.assertRaises(
            Operator.DoesNotExist, Operator.objects.get, pk=self.operator_1.pk)


class CardNumberAdminViewTestCase(TestCase):

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)

        # Create the file with Card numbers in CSV.
        self.csv_file = StringIO()
        self.csv_file.write('1A2B3C4D,12354\n3D4BFF54,90023\n9A6542BD,43021')
        self.csv_file.name = 'card_numbers.csv'

        self.url = reverse('admin:cards_cardnumber_importcsv')

    def tearDown(self):
        self.csv_file.close()

    def test_successful_post(self):
        """ Tests a successful POST of a CSV file """
        self.client.login(username=self.user.username, password='testing')
        response = self.client.post(
            self.url,
            data={
                'csv_file': SimpleUploadedFile(
                    self.csv_file.name, self.csv_file.getvalue())
            },
            follow=True)

        card_numbers = CardNumber.objects.all()

        self.assertEqual(len(card_numbers), 3)

        self.assertRedirects(
            response, reverse('admin:cards_cardnumber_changelist'))
