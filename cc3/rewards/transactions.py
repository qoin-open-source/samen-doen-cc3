import logging

from django.conf import settings
from django.utils.translation import ugettext_lazy, ugettext as _

from cc3.cyclos import backends
from cc3.cyclos.common import TransactionException
#from cc3.cyclos.models import User
from .models import UserCause#, DefaultGoodCause

LOG = logging.getLogger(__name__)


def cause_reward(amount, receiver, reward_transfer_id,
                 description=None,
                 fixed_donation_percentage=None):
    """
    Performs the transaction between a consumer user and the charity cause of
    his choice, if any.

    Returns ``None`` if the user did not selected any cause to contribute with
    donations or if there was a problem with the transaction in the Cyclos
    backend. If the transaction succeeds, returns the Cyclos transaction
    ``namedtuple`` object.

    :param amount: an integer representing the amount which was rewarded to
    the consumer initially
    :param receiver: the consumer, this is, the initial receiver of the reward
    :param reward_transfer_id: the cyclos transfer ID of the initial reward
    transaction from the business to the consumer
    :param fixed_donation_percentage: if set, all users pay that percentage;
    if None, use the user's own percentage, or fall back to the community
    default
    :return: the succeeded Cyclos ``Transaction`` ``namedtuple`` object or None
    """
    try:
        user_cause = UserCause.objects.get(consumer=receiver)
        cause = user_cause.cause
    except UserCause.DoesNotExist:
        # use the default good cause if one hasn't been set for a user
        LOG.error(u'Donation in transaction {0} failed. User {1} is not '
                  u'committed with any cause.'.format(reward_transfer_id,
                                                      receiver.pk))
        return None

#        user = User.objects.get(pk=receiver.pk)
#        cc3_community = user.cc3_profile.community
#        cause = DefaultGoodCause.objects.get(
#            community=cc3_community).cause

    # Apply donation percentage:
    # If fixed_donation_percentage supplied, use that for everyone; if None,
    # use the user-specific value from user_cause, falling back to community
    # default
    if fixed_donation_percentage is not None:
        percent = fixed_donation_percentage
    else:
        percent = user_cause.donation_percent
        if percent is None:
            percent = receiver.get_community().default_donation_percent

    if percent:
        donation = int(amount * percent / 100)

        # The receiver of the initial payment now donates the specified amount
        # to cause.

        # construct custom fields containing the transfer id of the
        # originating reward payment
        custom_fields = {
            "originating_transfer_id": reward_transfer_id,
            }

        try:
            transaction = backends.user_payment(
                receiver, cause, donation,
                description or _('Cause donation'),
                custom_fields=custom_fields)
        except TransactionException as e:
            LOG.warning(u'Unable to perform the donation '
                        u'transaction: {0}'.format(e))
            return None

        return transaction

    if percent == 0:
        # Legitimate zero percent configured, no donation to pay
        LOG.info(u"No donation for transaction {0}: donation percentage "
                 u"is zero for User {1}".format(reward_transfer_id,
                                                      receiver.pk))
    else:
        LOG.error(u'Donation in transaction {0} failed. User {1} does not '
                  u'have a community'.format(reward_transfer_id,
                                                      receiver.pk))
    return None
