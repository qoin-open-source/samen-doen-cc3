# -*- coding: utf-8 -*-
import json
import logging
from decimal import Decimal
from unittest import skipIf
from factory.fuzzy import FuzzyText

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.translation import ugettext as _

from mock import patch

from rest_framework.status import (
    HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_405_METHOD_NOT_ALLOWED)
from rest_framework.authtoken.models import Token

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.tests.test_factories import (
    UserFactory, CC3ProfileFactory, CyclosGroupFactory, CyclosGroupSetFactory,
    CC3CommunityFactory, CommunityRegistrationCodeFactory)
from cc3.cyclos.backends import set_backend
from cc3.rewards.tests.test_factories import (
    BusinessCauseSettingsFactory, UserCauseFactory,
    DefaultGoodCauseUserFactory)
from ..models import Card, CardNumber, CardTransaction, Operator, Terminal
from .test_factories import (
    TerminalFactory, OperatorFactory, CardFactory, CardNumberFactory)
from ..views_api import register_card, get_new_card_number

LOG = logging.getLogger(__name__)


class TerminalLoginViewTestCase(TestCase):

    def setUp(self):
        self.timestamp = timezone.now()

        self.url = reverse('api_cards_terminal_login')

    def test_terminal_login_get(self):
        """ Method GET not allowed """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)

    def test_terminal_login_unknown(self):
        """ Logging in with an unknown name is not possible """
        data = {
            'name': 'new_terminal'
        }

        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {"detail": "Terminal has not yet been registered to your account,"
                       " please do so via the website"})

    def test_terminal_login_empty_user(self):
        """Test logging in with a terminal that is not linked to a business"""
        terminal_1 = TerminalFactory.create(business=None)

        data = {
            'name': terminal_1.name
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {"detail": "Terminal has not yet been registered to your account,"
                       " please do so via the website"})

    @patch('django.utils.timezone.now')
    def test_terminal_login(self, mock):
        """ Test successful login using Terminal """
        mock.side_effect = [self.timestamp, self.timestamp, self.timestamp]

        user_1 = UserFactory.create()
        terminal_1 = TerminalFactory.create(business=user_1)

        data = {
            'name': terminal_1.name
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['id'], terminal_1.id)

        # Check Token
        self.assertEqual(Token.objects.all().count(), 1)
        token = Token.objects.get()
        self.assertEqual(data['token'], token.key)

        # Check `last_seen_date` timestamp.
        terminal = Terminal.objects.get(pk=terminal_1.pk)
        # Be aware that Django ORM does not store microseconds in MySQL.
        self.assertEqual(terminal.last_seen_date.year, self.timestamp.year)
        self.assertEqual(terminal.last_seen_date.month, self.timestamp.month)
        self.assertEqual(terminal.last_seen_date.day, self.timestamp.day)
        self.assertEqual(terminal.last_seen_date.hour, self.timestamp.hour)
        self.assertEqual(terminal.last_seen_date.minute, self.timestamp.minute)
        self.assertEqual(terminal.last_seen_date.second, self.timestamp.second)


class OperatorLoginViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('api_cards_operator_login')

        self.user_1 = UserFactory.create()
        self.terminal_1 = TerminalFactory.create(business=self.user_1)
        self.token_1 = Token.objects.create(user=self.user_1)
        self.operator_1 = OperatorFactory(business=self.user_1)
        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))

        self.timestamp = timezone.now()

    @patch('django.utils.timezone.now')
    def test_operator_login(self, mock):
        """ Test successful login by an operator """
        mock.return_value = self.timestamp

        data = {
            'name': self.operator_1.name,
            'pin': self.operator_1.pin,
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['id'], self.operator_1.id)
        self.assertEqual(data['user_id'], self.operator_1.business.id)

        # Check `last_login_date` timestamp.
        operator = Operator.objects.get(pk=self.operator_1.pk)
        # Be aware that Django ORM does not store microseconds in MySQL.
        self.assertEqual(operator.last_login_date.year, self.timestamp.year)
        self.assertEqual(operator.last_login_date.month, self.timestamp.month)
        self.assertEqual(operator.last_login_date.day, self.timestamp.day)
        self.assertEqual(operator.last_login_date.hour, self.timestamp.hour)
        self.assertEqual(operator.last_login_date.minute, self.timestamp.minute)
        self.assertEqual(operator.last_login_date.second, self.timestamp.second)

    def test_operator_login_nonexisting(self):
        """ Test invalid logging in, wrong operator name """
        data = {
            'name': 'nonexisting',
            'pin': self.operator_1.pin,
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(data['detail'], "Invalid operator or pin")

    def test_operator_login_invalid_pin(self):
        """ Test invalid logging in, wrong pin but correct operator name """
        data = {
            'name': self.operator_1.name,
            'pin': self.operator_1.pin + "1234"
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(data['detail'], "Invalid operator or pin")

    def test_operator_login_no_fields(self):
        """ Test invalid logging in, missing operator name & pin """
        data = {
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(data['detail'], "Invalid operator or pin")


class UserLoginViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('api_cards_user_login')

        self.user_1 = UserFactory.create()
        self.terminal_1 = TerminalFactory.create(business=self.user_1)
        self.token_1 = Token.objects.create(user=self.user_1)
        self.operator_1 = OperatorFactory(business=self.user_1)

        self.user_2 = UserFactory.create()

        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))

    def test_user_login(self):
        """ Test successful login by a user """
        data = {
            'email': self.user_2.email,
            'password': 'testing',
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['id'], self.user_2.id)

    def test_user_invalid_login(self):
        """ Test invalid login by a user """
        data = {
            'email': self.user_2.email,
            'password': 'thisisincorrect',
        }
        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(data['detail'], 'Invalid email address or password')


class CardRegisterViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('api_cards_card_register')

        self.card_number = CardNumberFactory.create()

        self.user_1 = UserFactory.create()
        self.terminal_1 = TerminalFactory.create(business=self.user_1)
        self.token_1 = Token.objects.create(user=self.user_1)
        self.operator_1 = OperatorFactory(business=self.user_1)

        self.user_2 = UserFactory.create()

        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))

    def test_card_register(self):
        """ Test successful card registration by a user """
        data = {
            'card': self.card_number.uid_number,
            'user_id': self.user_2.id
        }

        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)

        cards = Card.objects.all()

        # Check that the ``Card`` object was actually created.
        self.assertGreater(len(cards), 0)

        card = cards.latest('pk')
        data = json.loads(response.content)

        self.assertEqual(data['id'], card.id)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=True)
    def test_unknown_card_auto_create(self):
        """ Test unknown card registration by a user """

        data = {
            'card': FuzzyText(length=10).fuzz(),
            'user_id': self.user_2.id
        }

        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, HTTP_200_OK)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=False)
    def test_unknown_card_invalid(self):
        """ Test invalid card registration by a user """

        data = {
            'card': FuzzyText(length=10).fuzz(),
            'user_id': self.user_2.id
        }

        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(Card.objects.all().count(), 0)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=False)
    def test_unknown_card_auto_create_bad_user(self):
        """ Test unknown card registration by unknown user """

        data = {
            'card': FuzzyText(length=10).fuzz(),
            'user_id': self.user_2.id + 100
        }

        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(Card.objects.all().count(), 0)

    def test_card_duplicated(self):
        """
        Test integrity error handling when trying to register a card twice.
        """
        # Manually create a card.
        CardFactory.create(number=self.card_number, owner=self.user_2)

        # Test trying to create another card with the used card number.
        data = {
            'card': self.card_number.uid_number,
            'user_id': self.user_2.id
        }

        response = self.client.post(self.url, data=json.dumps(data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 409)

    def test_register_card_helper_success(self):
        """
        Tests the ``register_card`` helper function in a successful execution.
        """
        card = register_card(self.card_number, self.user_2)

        self.assertIsInstance(card, Card)

    def test_register_card_helper_fail(self):
        """
        Tests the ``register_card`` helper function in a failed execution.
        """
        # Manually create a card.
        CardFactory.create(number=self.card_number, owner=self.user_2)

        card = register_card(self.card_number, self.user_2)

        self.assertIsNone(card)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=False)
    def test_get_new_card_number(self):
        """
        Tests the ``get_new_card_number`` helper function fails if auto create
        cards not enabled for system
        """
        card_number = get_new_card_number(FuzzyText(length=10).fuzz())
        self.assertIsNone(card_number)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=True)
    def test_get_new_card_number(self):
        """
        Tests the ``get_new_card_number`` helper function fails if auto create
        cards not enabled for system
        """
        card_number = get_new_card_number(FuzzyText(length=10).fuzz())
        self.assertIsNotNone(card_number)


class CardDetailViewTestCase(TestCase):
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.user_1 = UserFactory.create()
        self.terminal_1 = TerminalFactory.create(business=self.user_1)
        self.token_1 = Token.objects.create(user=self.user_1)
        self.operator_1 = OperatorFactory(business=self.user_1)

        self.user_2 = UserFactory.create()
        self.cc3profile_2 = CC3ProfileFactory.create(user=self.user_2,
                                                     first_name='Test',
                                                     last_name='User')

        self.user_3 = UserFactory.create()

        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))
        self.card_2 = CardFactory.create(owner=self.user_2)
        self.card_3 = CardFactory.create(owner=self.user_3)
        self.blocked_card = CardFactory.create(owner=self.user_2)
        self.blocked_card.block_card()

    def test_card_details(self):
        """ Retrieve the details of a card/user combination """
        url = reverse(
            'api_cards_card_detail', args=[self.card_2.number.uid_number])

        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEquals(data['name'], self.cc3profile_2.full_name)
        self.assertEquals(data['username'], self.user_2.username)
        self.assertEquals(data['user_id'], self.user_2.id)
        self.assertEquals(data['balance'],
                          int(self.user_2.cc3_profile.current_balance))

    def test_card_details_no_cc3_profile(self):
        """ Fail when the user does not have a CC3 profile """
        url = reverse(
            'api_cards_card_detail', args=[self.card_3.number.uid_number])
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_card_details_invalid(self):
        """ Fail when the URL is invalid """
        url = reverse(
            'api_cards_card_detail', args=[self.card_2.number.uid_number])
        response = self.client.get(
            url + 'metnogmeer', content_type='application/json')
        self.assertNotEqual(response.status_code, HTTP_200_OK)

    def test_card_details_blocked(self):
        """ Fail when the Card is blocked"""
        url = reverse(
            'api_cards_card_detail', args=[self.blocked_card.number.uid_number])
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)


class CardPermittedDetailTest(TestCase):
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.user_1 = UserFactory.create()
        self.terminal_1 = TerminalFactory.create(business=self.user_1)
        self.token_1 = Token.objects.create(user=self.user_1)
        self.operator_1 = OperatorFactory(business=self.user_1)

        self.user_2 = UserFactory.create()
        self.cc3profile_2 = CC3ProfileFactory.create(user=self.user_2,
                                                     first_name='Test',
                                                     last_name='User')

        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))
        self.card_2 = CardFactory.create(owner=self.user_2)
        self.blocked_card = CardFactory.create(owner=self.user_2)
        self.blocked_card.block_card()

    def test_card_permitted_details(self):
        url = reverse(
            'api_cards_card_permitted_detail',
            args=[self.card_2.number.uid_number])

        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['card_number'], self.card_2.number.number)
        self.assertEqual(data['card_uid'], self.card_2.number.uid_number)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=True)
    def test_card_permitted_details_auto_create(self):
        new_card_number = FuzzyText(length=10).fuzz()
        url = reverse(
            'api_cards_card_permitted_detail',
            args=[new_card_number])

        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['card_uid'], new_card_number)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=False)
    def test_card_permitted_details_invalid(self):
        url = reverse(
            'api_cards_card_permitted_detail',
            args=[FuzzyText(length=10).fuzz()])

        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_card_permitted_details_blocked(self):
        """ Fail when the Card is blocked"""
        url = reverse(
            'api_cards_card_permitted_detail',
            args=[self.blocked_card.number.uid_number])
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)


class NewAccountViewTestCase(TestCase):
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.group_2 = CyclosGroupFactory.create()
        self.group_3 = CyclosGroupFactory.create()
        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, self.group_2, self.group_3])

        self.community = CC3CommunityFactory.create(
            groupsets=[self.groupset], code='TST')
        if 'cc3.rewards' in settings.INSTALLED_APPS:
            self.defaultgoodcause = DefaultGoodCauseUserFactory.create(
                community=self.community
            )
        self.reg_code = CommunityRegistrationCodeFactory.create(code="I",
            community=self.community, groupset=self.groupset)

        self.user = UserFactory.create()
        self.profile = CC3ProfileFactory.create(community=self.community)
        self.terminal_1 = TerminalFactory.create(business=self.profile.user)
        self.token_1 = Token.objects.create(user=self.profile.user)
        self.operator_1 = OperatorFactory(business=self.profile.user)

        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))

        # Invalid user (does not have any CC3Profile related, no business
        # available then).
        self.terminal_2 = TerminalFactory.create(business=self.user)
        self.token_2 = Token.objects.create(user=self.user)
        self.operator_2 = OperatorFactory(business=self.user)
        self.client_bad = self.client_class(
            HTTP_AUTHORIZATION='Token {0}'.format(self.token_2.key))

        self.card_number = CardNumberFactory.create(number='12345')
        self.url = reverse(
            'api_cards_card_new_account_detail', args=[
                self.card_number.uid_number])

    def test_new_account(self):
        """Test successful ``NewAccountView`` POST"""
        response = self.client.post(self.url, content_type='application/json')
        LOG.info("test_new_account self.url = {0}".format(self.url))
        self.assertEqual(response.status_code, HTTP_200_OK)

        # Check that the new ``CardNumber`` object has been created.
        card_nr = CardNumber.objects.get(number=self.card_number.number)
        data = json.loads(response.content)
        self.assertNotEqual(data['password'], '')
        self.assertEqual(data['email'], card_nr.card.owner.email)
        self.assertEqual(data['card_number'], unicode(card_nr.number))
        self.assertEqual(data['card_uid'], card_nr.uid_number)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=False)
    def test_new_account_non_registered_card(self):
        """Test ``NewAccountView`` returns 400 code when passing a non
        registered ``CardNumber`` code"""
        url = reverse(
            'api_cards_card_new_account_detail',
            kwargs={'card_number': 'INVALID_CODE'})

        response = self.client.post(url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    @override_settings(CC3_AUTO_CREATE_CARD_NUMBERS=True)
    def test_new_account_non_registered_card_auto_create(self):
        """Test ``NewAccountView`` is successful when settings
        allow auto creation of card numbers"""
        card_uid = FuzzyText(length=10).fuzz()
        url = reverse(
            'api_cards_card_new_account_detail',
            kwargs={'card_number': card_uid})

        response = self.client.post(url, content_type='application/json')
        LOG.info("test_new_account self.url = {0}".format(self.url))
        self.assertEqual(response.status_code, HTTP_200_OK)

        # Check that the new ``CardNumber`` object has been created.
        data = json.loads(response.content)
        self.assertNotEqual(data['password'], '')
        self.assertEqual(data['card_uid'], card_uid)

    @override_settings(CC3_CARDS_API_NEW_ACCOUNT_VIEW=None)
    def test_new_account_no_backend_available(self):
        """Test ``NewAccountView`` returns 400 code when no backend is
        available"""
        response = self.client.post(self.url, content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_new_account_business_does_not_exist(self):
        """Test ``NewAccountView`` returns 400 code when the request user
        CC3Profile does not exist"""
        response = self.client_bad.post(
            self.url, content_type='application/json')
        LOG.info("test_new_account_business_does_not_exist "
                 "self.url = {0}".format(self.url))

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_new_account_duplicated_card(self):
        """Test ``NewAccountView`` error handling when trying to register a
        duplicated card number"""
        # Create a Card that uses the existent ``CardNumber``.
        CardFactory.create(number=self.card_number, owner=self.user)

        response = self.client.post(self.url, content_type='application/json')

        self.assertEqual(response.status_code, 409)


class CardPaymentTest(TestCase):
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, ])
        self.community = CC3CommunityFactory.create(
            groupsets=[self.groupset], code='TST')

        self.user_1 = UserFactory.create()
        self.terminal_1 = TerminalFactory.create(business=self.user_1)
        self.token_1 = Token.objects.create(user=self.user_1)
        self.operator_1 = OperatorFactory(business=self.user_1)
        self.cc3profile_1 = CC3ProfileFactory.create(
            user=self.user_1, first_name='Test', last_name='Business',
            community=self.community, cyclos_group=self.group_1)
        self.user_2 = UserFactory.create()
        self.cc3profile_2 = CC3ProfileFactory.create(
            user=self.user_2, first_name='Test', last_name='User',
            community=self.community, cyclos_group=self.group_1)

        self.user_3 = UserFactory.create()

        self.user_4 = UserFactory.create()
        self.terminal_4 = TerminalFactory.create(business=self.user_4)
        self.token_4 = Token.objects.create(user=self.user_4)
        self.operator_4 = OperatorFactory(business=self.user_4)

        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))
        self.card_2 = CardFactory.create(owner=self.user_2)
        self.card_3 = CardFactory.create(owner=self.user_3)

        self.community_5 = CC3CommunityFactory.create(
            groupsets=[self.groupset])
        self.user_5 = UserFactory.create()
        self.cc3profile_5 = CC3ProfileFactory.create(
            user=self.user_5, first_name='Test', last_name='User5',
            community=self.community_5, cyclos_group=self.group_1)
        self.card_5 = CardFactory.create(owner=self.user_5)
        self.blocked_card = CardFactory.create(owner=self.user_2)
        self.blocked_card.block_card()

        self.url = reverse(
            'api_cards_card_payment', args=[self.card_2.number.uid_number])

    def test_card_pay_successful(self):
        """ Test a payment from a user/card-holder to the business owner """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.card_2.owner.id,
            'receiver_id': self.operator_1.business.id,
            'amount': '50',
            'description': 'My transaction'
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['transaction_id'],
                         self.backend.transactions()[0].transfer_id)
        trans = self.backend.transactions()[0]
        self.assertEqual(trans.amount, 50)
        self.assertEqual(trans.sender, self.card_2.owner)
        self.assertEqual(trans.recipient, self.operator_1.business)
        self.assertEqual(trans.description, 'My transaction')

    def test_card_pay_successful_decimal(self):
        """ Test a decimal payment from a user/card-holder to business owner """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.card_2.owner.id,
            'receiver_id': self.operator_1.business.id,
            'amount': '40.01',
            'description': 'My transaction'
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['transaction_id'],
                         self.backend.transactions()[0].transfer_id)
        trans = self.backend.transactions()[0]
        self.assertEqual(trans.amount, Decimal('40.01'))
        self.assertEqual(trans.sender, self.card_2.owner)
        self.assertEqual(trans.recipient, self.operator_1.business)
        self.assertEqual(trans.description, 'My transaction')

    def test_card_payment_operator_name_business_unique_together(self):
        """
        Test a payment operation when there is more than one ``Operator``
        object with the same ``name`` defined.

        Enforces the checkup of the 'unique together' relationship of the two
        fields in the ``Operator`` model, which is used in the API view
        ``CardTransactionView`` to retrieve the operator.
        """
        OperatorFactory(name=self.operator_1.name)
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.card_2.owner.id,
            'receiver_id': self.operator_1.business.id,
            'amount': '50',
            'description': 'My transaction'
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_card_receive(self):
        """ Test a payment from the business owner to the user/card-holder """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'receiver_id': self.card_2.owner.id,
            'sender_id': self.operator_1.business.id,
            'amount': '50',
            'description': 'My transaction'
        }
        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['transaction_id'],
                         self.backend.transactions()[0].transfer_id)
        trans = self.backend.transactions()[0]
        self.assertEqual(trans.amount, 50)
        self.assertEqual(trans.recipient, self.card_2.owner)
        self.assertEqual(trans.sender, self.operator_1.business)
        self.assertEqual(trans.description, 'My transaction')

    def test_card_receive_credit_limit(self):
        """ Test a payment from the business owner to the user/card-holder,
        where the balance of the business owner can become negative
        (DummyCyclosBackend credit limit: 50) """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'receiver_id': self.card_2.owner.id,
            'sender_id': self.operator_1.business.id,
            'amount': '149',
            'description': 'My transaction'
        }
        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['transaction_id'],
                         self.backend.transactions()[0].transfer_id)
        trans = self.backend.transactions()[0]
        self.assertEqual(trans.amount, 149)
        self.assertEqual(trans.recipient, self.card_2.owner)
        self.assertEqual(trans.sender, self.operator_1.business)
        self.assertEqual(trans.description, 'My transaction')

    def test_card_receive_credit_limit_invalid(self):
        """ Test a payment from the business owner to the user/card-holder,
        where the credit limit of the business owner is invalid.
        (DummyCyclosBackend credit limit: 50) """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'receiver_id': self.card_2.owner.id,
            'sender_id': self.operator_1.business.id,
            'amount': '151',
            'description': 'My transaction'
        }
        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_card_pay_invalid_terminal(self):
        """ Wrong terminal name """
        data = {
            'terminal_name': 'invalid',
            'operator_name': self.operator_1.name,
            'sender_id': self.card_2.owner.id,
            'receiver_id': self.operator_1.business.id,
            'amount': '50',
            'description': 'My transaction'
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_card_pay_invalid_operator(self):
        """ Wrong operator name """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': 'invalid',
            'sender_id': self.card_2.owner.id,
            'receiver_id': self.operator_1.business.id,
            'amount': '50',
            'description': 'My transaction'
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_card_pay_third_party_payment(self):
        """
        Unable to perform payments if we're not one of either party.
        Note that we authenticate with terminal_1/operator_1
        """
        data = {
            'terminal_name': self.terminal_4.name,
            'operator_name': self.operator_4.name,
            'sender_id': self.card_2.owner.id,
            'receiver_id': self.operator_4.business.id,
            'amount': '50',
            'description': 'My transaction'
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_card_pay_same_sender_receiver(self):
        """ Can't send payments if the user is both sender and receiver """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.card_2.owner.id,
            'receiver_id': self.card_2.owner.id,
            'amount': '50',
            'description': 'My transaction'
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_card_pay_wrong_card(self):
        """ The payment must be made on the correct card resource """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.card_3.owner.id,
            'receiver_id': self.operator_1.business.id,
            'amount': '50',
            'description': 'My transaction'
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_card_pay_from_blocked_card(self):
        """ The payment must be from a non-blocked card """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.blocked_card.owner.id,
            'receiver_id': self.card_2.owner.id,
            'amount': '50',
            'description': 'My transaction'
        }
        url = reverse(
            'api_cards_card_payment', args=[self.blocked_card.number.uid_number])

        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=False)
    def test_card_pay_inter_community_not_possible(self):
        """ Testing INTER_COMMUNITIES_TRANSACTIONS=False blocks """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.card_5.owner.id,
            'receiver_id': self.operator_1.business.id,
            'amount': '50',
            'description': 'My transaction'
        }
        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_card_pay_inter_community_possible(self):
        """ Testing INTER_COMMUNITIES_TRANSACTIONS=True allows """
        data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.card_2.owner.id,
            'receiver_id': self.operator_1.business.id,
            'amount': '50',
            'description': 'My transaction'
        }
        response = self.client.post(
            self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, HTTP_200_OK)


class CardRewardTest(TestCase):
    """
    Test case for the ``CardRewardView`` API view.

    Rewards must be performed by following this schema:

    1 - The business transfers the reward amount to the consumer.
    2 - A fixed percentage (by default the 40%) of that amount is deducted
    for the consumer cause.
    3 - The consumer transfers that percentage of the reward amount to the
    cause.

    Then, two transactions must be performed and also logged to the system.
    """
    @skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
            u'Skipped as cc3.rewards app not enabled')
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.group_1 = CyclosGroupFactory.create(initial=True)
        self.groupset = CyclosGroupSetFactory.create(
            groups=[self.group_1, ])
        self.community = CC3CommunityFactory.create(
            groupsets=[self.groupset], code='TST')

        # Create business with its terminal.
        self.user_1 = UserFactory.create()
        self.terminal_1 = TerminalFactory.create(business=self.user_1)
        self.token_1 = Token.objects.create(user=self.user_1)
        self.operator_1 = OperatorFactory(business=self.user_1)
        self.cc3profile_1 = CC3ProfileFactory.create(
            user=self.user_1, first_name='Test', last_name='Business',
            community=self.community, cyclos_group=self.group_1)
        self.business_settings = BusinessCauseSettingsFactory.create(
            user=self.user_1)

        # Create card users.
        self.user_2 = UserFactory.create()
        self.cc3profile_2 = CC3ProfileFactory.create(
            user=self.user_2, first_name='Test', last_name='User',
            community=self.community, cyclos_group=self.group_1)
        self.user_cause = UserCauseFactory.create(consumer=self.user_2)

        self.community_2 = CC3CommunityFactory.create(
            groupsets=[self.groupset], code='TST')

        self.user_3 = UserFactory.create()
        self.cc3profile_3 = CC3ProfileFactory.create(
            user=self.user_3, first_name='Test', last_name='User',
            community=self.community_2, cyclos_group=self.group_1)

        self.user_4 = UserFactory.create()
        self.terminal_4 = TerminalFactory.create(business=self.user_4)
        self.token_4 = Token.objects.create(user=self.user_4)
        self.operator_4 = OperatorFactory(business=self.user_4)

        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))
        self.card_2 = CardFactory.create(owner=self.user_2)
        self.card_3 = CardFactory.create(owner=self.user_3)

        self.url = reverse(
            'api_cards_card_reward', args=[self.card_2.number.uid_number])

        self.post_data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.operator_1.business.id,
            'receiver_id': self.card_2.owner.id,
            'amount': '100',
            'description': 'Reward to good cause {0}'.format(
                self.user_cause.cause)
        }

    @skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
            u'Skipped as cc3.rewards app not enabled')
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_card_reward_business_to_consumer_transaction(self):
        """
        Tests the transaction from business to consumer performed during a
        successful reward operation.
        """
        response = self.client.post(
            self.url, data=json.dumps(self.post_data),
            content_type='application/json')

        self.assertEqual(response.status_code, HTTP_200_OK)

        data = json.loads(response.content)

        self.assertEqual(data['card_transaction_id'],
                         self.backend.transactions()[0].transfer_id)

        # Check the transaction from business to consumer.
        trans = self.backend.transactions()[0]
        self.assertEqual(trans.amount, 100)
        self.assertEqual(trans.sender, self.terminal_1.business)
        self.assertEqual(trans.recipient, self.card_2.owner)
        self.assertEqual(trans.description, self.post_data['description'])

    @skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
            u'Skipped as cc3.rewards app not enabled')
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_card_reward_consumer_to_cause_transaction(self):
        """
        Tests the transaction from consumer to cause performed during a
        successful reward operation.
        """
        response = self.client.post(
            self.url, data=json.dumps(self.post_data),
            content_type='application/json')

        self.assertEqual(response.status_code, HTTP_200_OK)

        data = json.loads(response.content)

        self.assertEqual(data['reward_transaction_id'],
                         self.backend.transactions()[1].transfer_id)

        # Check the transaction from consumer to cause.
        # It must be the 40% of the initial transaction.
        trans = self.backend.transactions()[1]
        self.assertEqual(trans.amount, 40)
        self.assertEqual(trans.sender, self.card_2.owner)
        self.assertEqual(trans.recipient, self.user_cause.cause)
        self.assertEqual(trans.description, _('Cause donation'))

    @skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
            u'Skipped as cc3.rewards app not enabled')
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_card_reward_transaction_logged(self):
        """
        Tests the creation of ``Transaction`` objects to log the rewarding.

        There must be 2 ``Transaction``s logged: one from the business to the
        consumer and another one from the consumer to the cause.
        """
        response = self.client.post(
            self.url, data=json.dumps(self.post_data),
            content_type='application/json')

        self.assertEqual(response.status_code, HTTP_200_OK)

        transactions = CardTransaction.objects.all()
        self.assertEqual(len(transactions), 2)

    @skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
            u'Skipped as cc3.rewards app not enabled')
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_card_reward_invalid_terminal(self):
        """ Test wrong terminal name when performing a reward """
        self.post_data['terminal_name'] = 'invalid'

        response = self.client.post(
            self.url, data=json.dumps(self.post_data),
            content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    @skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
            u'Skipped as cc3.rewards app not enabled')
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_card_reward_invalid_operator(self):
        """ Test wrong operator name when performing a reward """
        self.post_data['operator_name'] = 'invalid'

        response = self.client.post(
            self.url, data=json.dumps(self.post_data),
            content_type='application/json')
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

# TODO, test to check community and user values are used appropriately
    #@override_settings(INTER_COMMUNITIES_TRANSACTIONS=True,
    #                   REWARDS_FIXED_PERCENTAGE=None)
    #@skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
    #        u'Skipped as cc3.rewards app not enabled')
    #def test_card_reward_fixed_percentage_setting(self):
    #    """
    #    Test automatic fallback when ``REWARDS_FIXED_PERCENTAGE`` setting is
    #    missing.
    #    """
    #    # Delete the setting.
    #    del settings.REWARDS_FIXED_PERCENTAGE
    #
    #    response = self.client.post(
    #        self.url, data=json.dumps(self.post_data),
    #        content_type='application/json')
    #
    #    self.assertEqual(response.status_code, HTTP_200_OK)
    #
    #    data = json.loads(response.content)
    #
    #    self.assertEqual(data['reward_transaction_id'],
    #                     self.backend.transactions()[1].transfer_id)
    #
    #    # Check the transaction from consumer to cause.
    #    # It must be the 40% of the initial transaction.
    #    trans = self.backend.transactions()[1]
    #    self.assertEqual(trans.amount, 40)
    #    self.assertEqual(trans.sender, self.card_2.owner)
    #    self.assertEqual(trans.recipient, self.user_cause.cause)
    #    self.assertEqual(trans.description, _('Cause donation'))

    @skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
            u'Skipped as cc3.rewards app not enabled')
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_card_reward_no_cause_available(self):
        """
        Tests that the request returns a 400 error when the user has no
        charity cause configured.
        """
        url = reverse(
            'api_cards_card_reward', args=[self.card_3.number.uid_number])

        post_data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.operator_1.business.id,
            'receiver_id': self.card_3.owner.id,
            'amount': '100',
            'description': 'Reward to good cause {0}'.format(
                self.user_cause.cause)
        }

        response = self.client.post(
            url, data=json.dumps(post_data), content_type='application/json')

        self.assertEqual(response.status_code, HTTP_200_OK)

        data = json.loads(response.content)

        self.assertIsNone(data['reward_transaction_id'])

    @skipIf(not 'cc3.rewards' in settings.INSTALLED_APPS,
            u'Skipped as cc3.rewards app not enabled')
    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=False)
    def test_card_reward_inter_community_fails(self):
        """
        Tests that the request returns a 400 error when the reward is attempted
        to a business and/or cause in a different community.

        NB this relies on the fact that all users in these
        tests are in different communities
        """
        url = reverse(
            'api_cards_card_reward', args=[self.card_3.number.uid_number])

        post_data = {
            'terminal_name': self.terminal_1.name,
            'operator_name': self.operator_1.name,
            'sender_id': self.operator_1.business.id,
            'receiver_id': self.card_3.owner.id,
            'amount': '100',
            'description': 'Reward to good cause {0}'.format(
                self.user_cause.cause)
        }

        response = self.client.post(
            url, data=json.dumps(post_data), content_type='application/json')

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
