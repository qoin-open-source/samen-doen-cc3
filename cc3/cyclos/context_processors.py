import logging
from xml.parsers.expat import ExpatError

from cc3.cyclos import backends
from cc3.cyclos.services import MemberNotFoundException
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _


LOG = logging.getLogger(__name__)


def balance(request):
    _balance = upper_credit_limit = lower_credit_limit = None
    has_account = False

    if request.user.is_authenticated():
        if not request.user.is_superuser:
            try:
                # http://www.cyclos.org/wiki/index.php/Web_services#Model_data_details
                account_status = backends.get_account_status(
                    request.user.username).accountStatus
                _balance = account_status.balance
                upper_credit_limit = account_status.upperCreditLimit
                lower_credit_limit = account_status.creditLimit
                has_account = True
            except MemberNotFoundException:
                LOG.info(u"Member '{0}' not present in Cyclos backend".format(
                    request.user))
                has_account = False
                _balance = None
            # except ExpatError:
            #     LOG.info(u"Member '{0}' not present in Cyclos backend".format(
            #         request.user))
            #     has_account = False
            #     _balance = None
            except ExpatError as e:
                messages.add_message(
                    request, messages.WARNING, _("Unable to get account "
                                                 "details at present"))
                LOG.info(u"Exception {0}".format(e))
                has_account = False
                _balance = None

    if upper_credit_limit:
        upper_credit_limit = int(upper_credit_limit)
    if lower_credit_limit:
        lower_credit_limit = int(lower_credit_limit)
    return {
        'balance': _balance,
        'has_account': has_account,
        'upper_credit_limit': upper_credit_limit,
        'lower_credit_limit': lower_credit_limit
    }
