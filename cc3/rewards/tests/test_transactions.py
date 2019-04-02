from django.test import TestCase

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.tests.test_factories import CC3ProfileFactory

from .test_factories import UserCauseFactory#, DefaultGoodCauseUserFactory
from ..transactions import cause_reward


class CauseRewardTestCase(TestCase):
    """
    Test case for the ``cause_reward`` function.
    """
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.consumer = CC3ProfileFactory.create()
        self.cause = CC3ProfileFactory.create()

        self.user_cause = UserCauseFactory.create(
            consumer=self.consumer.user, cause=self.cause.user)

        self.consumer.community.min_donation_percent = 20
        self.consumer.community.max_donation_percent = 60
        self.consumer.community.default_donation_percent = 40
        self.consumer.community.save()


    def test_successful_donation(self):
        """
        Tests a successful donation. Taking 100 bucks rewarded, the donation
        should consist in 40 bucks donated from the consumer to the cause.
        """
        transaction = cause_reward(100, self.consumer.user, 1)

        # It should return a ``Transaction`` namedtuple.
        self.assertIsNotNone(transaction)

        # Check up the returned transaction data.
        self.assertEqual(transaction.sender, self.consumer.user)
        self.assertEqual(transaction.recipient, self.cause.user)
        self.assertEqual(transaction.amount,
                         self.consumer.community.default_donation_percent)

    def test_failed_donation_user_not_committed(self):
        """
        Tests a failed donation when the user is not committed with any cause.
        """
        # Create new user, not related with any cause.
        consumer = CC3ProfileFactory.create()
#        default_good_cause = DefaultGoodCauseUserFactory.create(
#            community=consumer.community
#        )

        transaction = cause_reward(100, consumer.user, 1)

        self.assertIsNone(transaction)
        # self.assertEqual(transaction.sender, consumer.user)
        # self.assertEqual(transaction.recipient,
        #                  default_good_cause.cause)
        # self.assertEqual(transaction.amount, 40)

    def test_user_override_percentage(self):
        """
        Tests that a user-specific reward percentage is used if it exists
        """
        self.user_cause.donation_percent = 50
        self.user_cause.save()
        transaction = cause_reward(100, self.consumer.user, 1)
        self.assertEqual(transaction.amount, 50)

    # def test_default_good_cause_donation_user_not_committed(self):
    #     """
    #     Tests a donation goes to the default good cause
    #     when the user is not committed with any cause.
    #     """
    #     # Create new user, not related with any cause.
    #     consumer = CC3ProfileFactory.create()
    #     default_good_cause = DefaultGoodCauseUserFactory.create(
    #         community=consumer.community
    #     )
    #
    #     transaction = cause_reward(100, consumer.user, 1)
    #
    #     self.assertEqual(transaction.sender, consumer.user)
    #     self.assertEqual(transaction.recipient,
    #                      default_good_cause.cause)
    #     self.assertEqual(transaction.amount, 40)
