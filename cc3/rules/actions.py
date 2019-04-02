import logging

from cc3.cyclos.models.account import User
from cc3.cyclos import backends

LOG = logging.getLogger(__name__)


class PayCC3Profile(object):
    """
    Example of Action class
    """
    def perform(self, *args, **kwargs):
        """
        Kwargs must match those set in parameter_keys and parameter_values for a rule

        This one written as proof of concept for tests, however, not successful in writing
        test due to cyclos dependency / interactions / groups etc.
        :param id:
        :param amount:
        :param sender:
        :return:
        """
        LOG.debug(kwargs)
        amount = kwargs['amount']
        sender_id = kwargs['sender_id']
        LOG.info(u"Action PayCC3Profile perform called id {0} amount {1} sender_id {2}".format(id, amount, sender_id))

        user = User.objects.get(pk=id)
        cc3_profile = user.get_cc3_profile()
        sender_user = User.objects.get(pk=sender_id)
        sender_profile = sender_user.get_cc3_profile()
        try:
            backends.user_payment(sender_profile, cc3_profile, amount, "Payment by action")
        except Exception, e:
            LOG.error(u"Action PayCC3Profile failed with {0}".format(e))
            return u"Action PayCC3Profile failed {0}".format(e)

        return u"Action PayCC3Profile succeeded id {0} amount {1} sender_id {2}".format(id, amount, sender_id)
