import logging
import random
from uuid import uuid4

from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from pysimplesoap.client import SoapFault

from .services import (
    Access, AccountNotFoundException, Accounts, Members,
    MemberNotFoundException, Payment, Payments)
from .common import AccountException, Transaction, TransactionException


LOG = logging.getLogger(__name__)


CYCLOS_URL = getattr(settings, 'CYCLOS_URL', 'http://localhost:8080')
BASIC_AUTH_ENABLED = getattr(settings, 'CYCLOS_BASIC_AUTH', False)
BASIC_AUTH_USER = getattr(settings, 'CYCLOS_BASIC_AUTH_USER', None)
BASIC_AUTH_PASS = getattr(settings, 'CYCLOS_BASIC_AUTH_PASS', None)

WEBSERVICE_TRACE = getattr(settings, 'CYCLOS_WEBSERVICE_TRACE', False)
WEBSERVICE_USE_CACHE = getattr(settings, 'CYCLOS_WEBSERVICE_WSDL_CACHE', False)

CYCLOS_REQUIRED_MEMBER_CREDENTIAL_FIELD = getattr(
    settings, 'CYCLOS_REQUIRED_MEMBER_CREDENTIAL_FIELD', 'login_password')

MEMBER_GROUP = getattr(
    settings, 'CYCLOS_CUSTOMER_MEMBER_GROUP', u'Customer Member')

MEMBER_TRANSACTION_NAME = getattr(
    settings, 'CYCLOS_FULL_MEMBER_TRANSACTION_TYPE',
    u'Consumer trade transfer (C2C or C2B)')


def get_shared_instance():
    raise Exception('Obsolete')


class CyclosBackend(object):
    def __init__(self):
        LOG.info('Initializing Cyclos backend')
        service_settings = {'base_location': CYCLOS_URL}
        if BASIC_AUTH_ENABLED:
            service_settings['basic_auth_user'] = BASIC_AUTH_USER
            service_settings['basic_auth_pass'] = BASIC_AUTH_PASS
        if WEBSERVICE_TRACE:
            service_settings['trace'] = True
        if WEBSERVICE_USE_CACHE:
            service_settings['cache'] = True
        self.members = Members(**service_settings)
        self.payments = Payments(**service_settings)
        self.accounts = Accounts(**service_settings)
        self.access = Access(**service_settings)

        self.member_transaction = None
        self.member_to_charity_transaction = None

        # ID of group for new members
        # also used in accounts/views to check if user has a trial account
        # TODO remove this, in favour of CyclosGroups and Groupsets
        self.member_group_id = None

        self._init_transaction_types()
#        self._init_member_groups()

#    def _init_member_groups(self):
#        groups = self.members.listManagedGroups()

#        for group in groups:
#            if group.name == MEMBER_GROUP:
#                self.member_group_id = group.id
#                return
#        raise ValueError(u'Cyclos group for members {0} not found'.format(MEMBER_GROUP))

    def _init_transaction_types(self):
        # only reason for this method is to set the self.member_transaction
        # for the backend, so once set, no need to call cyclos
        if self.member_transaction:
            pass

        available_transfer_types = self.accounts.search_transfer_types()
        for transfer_type in available_transfer_types:
            if transfer_type.name == MEMBER_TRANSACTION_NAME:
                self.member_transaction = transfer_type

    def new(self, username, name, email, business_name, initial_group_id,
            community_code=None, extra_fields=None):
        """ Create a new account in CC3/Cyclos. """
        logging.debug(u'Creating new CC3 account for {0}'.format(name))

        login_password = pin = None
        if CYCLOS_REQUIRED_MEMBER_CREDENTIAL_FIELD == 'login_password':
            login_password = _generate_dummy_password()
        else:
            pin = _generate_dummy_pin()

        custom_fields = []
        if business_name is not None:
            cyclos_business_name_field_internal_name = getattr(
                settings, "CC3_PROFILE_BUSINESS_NAME_FIELD_INTERNAL_NAME",
                u'Business'
            )
            custom_fields.append(
                {u'internalName': cyclos_business_name_field_internal_name,
                 u'value': business_name}
            )

        if community_code:
            custom_fields.append(
                {u'internalName': u'community', u'value': community_code})

        if extra_fields:
            for key, value in extra_fields.iteritems():
                custom_fields.append(
                    {u'internalName': key, u'value': value})

        try:
            new_member = self.members.register(
                username,
                name,
                email,
                login_password=login_password,
                pin=pin,
                group_id=initial_group_id,
                fields=custom_fields
            )

            return new_member
        except SoapFault as sf:
            LOG.error(username)
            LOG.error(name)
            LOG.error(email)
            LOG.exception(sf)
            raise AccountException(sf.args[1])

    def update(self, id, name, email, business_name, community_code=None,
               extra_fields=None):
        """
        Update the profile data in CC3/Cyclos.
        """

        #cyclos_id = cc3_profile.cyclos_account.cyclos_id
        #name = u"%s %s" % (cc3_profile.first_name, cc3_profile.last_name)

        custom_fields = []
        if business_name is not None:
            cyclos_business_name_field_internal_name = getattr(
                settings, "CC3_PROFILE_BUSINESS_NAME_FIELD_INTERNAL_NAME",
                u'Business'
            )

            custom_fields.append(
                {u'internalName': cyclos_business_name_field_internal_name,
                 u'value': business_name})

        if community_code:
            custom_fields.append({
                u'internalName': u'community',
                u'value': community_code
            })

        if extra_fields:
            for key, value in extra_fields.iteritems():
                custom_fields.append(
                    {u'internalName': key, u'value': value})

        self.members.update(
            id,
            name,
            email,
            fields=custom_fields
        )

    def update_group(self, id, group_id, comments):
        """ Update the group in CC3/Cyclos. """
        self.members.updateGroup(
            id,
            group_id,
            comments
        )

    def get_group(self, email):
        values = self.search(email=email)
        if values:
            return int(values[0][4])

    def user_payment(self, sender, receiver, amount, description,
                     transfer_type_id=None, custom_fields=None):
        return self._do_payment(sender, receiver, amount, description,
                                transfer_type_id, custom_fields=custom_fields)

    def _do_payment(self, sender, receiver, amount, description,
                    transfer_type_id=None, custom_fields=None):
        if self.member_transaction is not None and transfer_type_id is None:
            transfer_type_id = self.member_transaction.id

        fields = []
        # custom_fields is a dict, with key,value for each custom field
        # ... turn it into a list of fields
        if custom_fields:
            for key, value in custom_fields.iteritems():
                fields.append(
                    {u'internalName': key, u'value': value})

        payment = self.payments.doPayment(
            fromMember=sender, toMember=receiver, amount=amount,
            description=description, transferTypeId=transfer_type_id,
            customValues=fields)

        if payment.status == Payment.STATUS_PROCESSED:
            transfer = payment.transfer
            return Transaction(
                sender=sender,
                recipient=receiver,
                amount=transfer.amount,
                description=description,
                created=transfer.processDate,
                transfer_id=transfer.id
            )
        else:
            # Only parallel transactions could cause STATUS_NOT_ENOUGH_CREDITS
            # For all other status the user can't do anything, so:
            msg = "Payment status: {}".format(payment.status)
            raise TransactionException(msg)

    def to_system_payment(self, sender, amount, description, transfer_type_id):

        payment = self.payments.doPayment(
            amount,
            fromMember=sender,
            toSystem=True,
            transferTypeId=transfer_type_id,
            description=description
        )

        if payment.status == Payment.STATUS_PROCESSED:
            transfer = payment.transfer
            return Transaction(
                sender=sender,
                recipient=None,
                amount=transfer.amount,
                description=description,
                created=transfer.processDate,
                transfer_id=transfer.id
            )
        else:
            raise TransactionException(
                u"Payment status: {}".format(payment.status))

    def from_system_payment(self, receiver, amount, description, transfer_type_id):
        payment = self.payments.doPayment(
            amount,
            toMember=receiver,
            fromSystem=True,
            transferTypeId=transfer_type_id,
            description=description
        )

        if payment.status == Payment.STATUS_PROCESSED:
            transfer = payment.transfer
            return Transaction(
                sender=None,
                recipient=receiver,
                amount=transfer.amount,
                description=description,
                created=transfer.processDate,
                transfer_id=transfer.id
            )
        else:
            raise TransactionException(
                u"Payment status: {}".format(payment.status))

    def user_to_partner_payment(self, sender, partner_account_username, amount,
                                description):
        return self._do_member_to_partner_payment(
            sender, partner_account_username, None, amount, description)

    def _do_member_to_partner_payment(self, sender, partner_account_username,
                                      cc3_request, amount, description):
        transfer_id = None
        if self.member_to_partner_transaction is not None:
            transfer_id = self.member_to_partner_transaction.id

        payment = self.payments.doPayment(fromMember=sender.username,
                                toMember=partner_account_username,
                                amount=amount, description=description,
                                transferTypeId=transfer_id)
        if payment.status == Payment.STATUS_PROCESSED:
            transfer = payment.transfer
            return Transaction(
                sender=sender, recipient=partner_account_username,
                amount=transfer.amount, description=description,
                created=transfer.processDate, transfer_id=transfer.id)
        else:
            # Only parallel transactions could cause STATUS_NOT_ENOUGH_CREDITS
            # For all other status the user can't do anything, so:
            msg = "Payment status: {}".format(payment.status)
            raise TransactionException(msg)

    def transactions(self, username=None, description=None, from_to=None,
                     from_date=None, to_date=None, direction=None,
                     community=None, account_type_id=None,
                     currency=None):
        custom_fields = []
        if community:
            # NB SOAP call fails if a list is used.
            # TODO check why SOAP call fails with custom field list
            custom_fields = {u'internalName': u'community', u'value': community}
            # alternativ which works in TQ1.1 - very odd
            # custom_fields.append({u'internalName': u'community', u'value': community})

        return PageableTransactions(
            username=username,
            accounts=self.accounts,
            description=description,
            from_to=from_to,
            from_date=from_date,
            to_date=to_date,
            direction=direction,
            currency=currency,
            account_type_id=account_type_id,
            custom_fields=custom_fields
        )

    def user_fund_donation(self, sender, amount, description):
        transfer_id = None

        if self.donation_transaction is not None:
            transfer_id = self.donation_transaction.id
        custom_values = _get_custom_donation_fields(description)
        payment = self.payments.doPayment(
            fromMember=sender.username,
            toSystem=True,
            transferTypeId=transfer_id,
            amount=amount, description=description,
            customValues=custom_values
        )

        if payment.status == Payment.STATUS_PROCESSED:
            transfer = payment.transfer
            return Transaction(
                sender=sender, recipient=None, amount=transfer.amount,
                description=description, created=transfer.processDate,
                transfer_id=transfer.id)
        else:
            msg = "Payment status: {}".format(payment.status)
            raise TransactionException(msg)

#    def system_donation(self, receiver, donation):
#        account = _get_account(receiver) # make sure it's created
#        description = donation.description #TODO: don't use text from database
#        transfer_id = None
#        if self.org_transaction is not None:
#            transfer_id = self.org_transaction.id
#        custom_values = _get_custom_system_donation_fields(donation,
#                                                           description)
#        payment = self.payments.doPayment(
#                        fromSystem=True,
#                        toMember=receiver.username,
#                        transferTypeId=transfer_id,
#                        amount=donation.amount, description=description,
#                        customValues=custom_values
#                        )
#        if payment.status == Payment.STATUS_PROCESSED:
#            transfer = payment.transfer
#            return Transaction(sender=None, recipient=receiver,
#                               amount=transfer.amount, description=description,
#                               created=transfer.processDate,
#                               transfer_id=transfer.id)
#        else:
#            msg = "Payment status: {}".format(payment.status)
#            raise TransactionException(msg)

#    def get_balance(self, user):
#        """ Get current credits balance"""
#        cc3_profile = user.get_profile()
#        if not cc3_profile.cyclos_account:
#            raise ValueError('Linked CyclosAccount instance required')
#
#        account_history = self.accounts.searchHistory(
#                                     principal=cc3_profile.user.username,
#                                     principalType='USER',
#                                     pageSize=0)
#        return account_history.accountStatus.balance

#    def get_available_balance(self, user):
#        """ Get current credits balance"""
#        cc3_profile = user.get_profile()
#        if not cc3_profile.cyclos_account:
#            raise ValueError('Linked CyclosAccount instance required')
#
#        account_history = self.accounts.searchHistory(
#                                     principal=cc3_profile.user.username,
#                                     principalType='USER',
#                                     pageSize=0)
#        return account_history.accountStatus.availableBalance

#    def get_credit_limit(self, user):
#        """ Get current credit limit"""
#        cc3_profile = user.get_profile()
#        if not cc3_profile.cyclos_account:
#            raise ValueError('Linked CyclosAccount instance required')
#
#        account_history = self.accounts.searchHistory(
#                                     principal=cc3_profile.user.username,
#                                     principalType='USER',
#                                     pageSize=0)
#        return account_history.accountStatus.creditLimit

    def get_account_status(self, username):
        account_history = self.accounts.searchHistory(
            principal=username,
            principalType='USER',
            pageSize=0
        )
        return account_history

#    def get_total_count(self, username):
#        """ Get total transaction count"""
#        account_history = self.accounts.searchHistory(
#                                     principal=username,
#                                     principalType='USER',
#                                     pageSize=0)
#        return account_history.totalCount

    def list_members(self, currentPage=None, pageSize=None, keywords=None,
                     email=None, groupIds=None, groupFilterIds=None,
                     fields=None, showCustomFields=None, showImages=None):
        """
        List members by using Cyclos member fullTextSearch.
        Added for use in Django admin to get partner members/

        """
        if email:
            raise Exception('Cyclos3.6.1 bug - no full text search using email')

        return self.members.fullTextSearch(
            currentPage=currentPage, pageSize=pageSize, keywords=keywords,
            email=email, groupIds=groupIds, groupFilterIds=groupFilterIds,
            fields=fields, showCustomFields=showCustomFields,
            showImages=showImages)

    def member_fields(self):
        return self.fields.memberFieldsForMemberSearch()

    def search(self, currentPage=None, pageSize=None, username=None, name=None,
               email=None, randomOrder=False,groupIds=None,
               groupFilterIds=None, fields=None, showCustomFields=None,
               showImages=None):
        return self.members.search(
            currentPage=currentPage, pageSize=pageSize, username=username,
            email=email, name=name, randomOrder=randomOrder, groupIds=groupIds,
            groupFilterIds=groupFilterIds, fields=fields,
            showCustomFields=showCustomFields, showImages=showImages)

    def is_channel_enabled_for_member(self, username, channel_type=None):
        return self.access.isChannelEnabledForMember(username,
                                                     channel_type)

    def check_channel(self, username, channel_internal_name):
        return self.access.checkChannel(username, channel_internal_name)

    def change_channels(self, username, channels):
        return self.access.changeChannels(username, channels)


def _cyclos_transfer_to_transaction(transfer, user):
    if user:
        if transfer.systemAccountName is not None:
            return _convert_cyclos_system_transfer(transfer, user)
        else:
            return _convert_cyclos_member_transfer(transfer, user)
    # group - ie multiple users transactions
    else:
        return _convert_cyclos_transfer(transfer)


def _convert_cyclos_system_transfer(transfer, user):
    transfer_type = transfer.transferType
    from_ = transfer_type.from_
    to = transfer_type.to

    if from_.name == transfer.systemAccountName:
        sender = transfer.systemAccountName
    else:
        sender = user  # current user?
    if to.name == transfer.systemAccountName:
        recipient = transfer.systemAccountName
    else:
        recipient = user  # current user?

    return Transaction(sender=sender, recipient=recipient,
                       amount=transfer.amount,
                       created=transfer.processDate,
                       description=transfer.description,
                       transfer_id=transfer.id,
                       transfer_type_id=transfer_type.id)


def _convert_cyclos_member_transfer(transfer, user):
    from cc3.cyclos.models import CC3Profile

    member = transfer.member
    amount = transfer.amount

    #cyclos_id = cc3_profile.cyclos_account.cyclos_id
    member_cc3_profile = None
    try:
        member_cc3_profile = CC3Profile.viewable.get(
            cyclos_account__cyclos_id=member.id)
    except CC3Profile.DoesNotExist:
        logging.debug(
            'Cannot find profile for cyclos account id {0}'.format(member.id))

    if member_cc3_profile:
        member_user = member_cc3_profile.user
    else:
        member_user = member.name

    if amount.is_signed():
        sender = user  # current user
        recipient = member_user
    else:
        sender = member_user
        recipient = user  # current user

    return Transaction(
        sender=sender, recipient=recipient, amount=transfer.amount,
        created=transfer.processDate, description=transfer.description,
        transfer_id=transfer.id, transfer_type_id=transfer.transferType.id)


def _convert_cyclos_transfer(transfer):
    from cc3.cyclos.models import CC3Profile
    # user not known, so work with what we've got from cyclos
    transfer_type = transfer.transferType

    from_ = transfer_type.from_
    to = transfer_type.to
    if transfer.fromMember:
        try:
            sender_cc3_profile = CC3Profile.viewable.get(cyclos_account__cyclos_id=transfer.fromMember['id'])
            sender = sender_cc3_profile.user
        except Exception, e:
            logging.debug('Cannot find profile for cyclos account id %s' % transfer.fromMember['id'])
            sender = transfer.fromMember['name']
    else:
        sender = from_.name
    if transfer.member:
        try:
            recipient_cc3_profile = CC3Profile.viewable.get(cyclos_account__cyclos_id=transfer.member.id)
            recipient = recipient_cc3_profile.user
        except Exception, e:
            logging.debug('Cannot find profile for cyclos account id %s' % transfer.member.id)
            recipient = transfer.member.name
    else:
        recipient = to.name

    return Transaction(sender=sender, recipient=recipient,
                       amount=transfer.amount,
                       created=transfer.processDate,
                       description=transfer.description,
                       transfer_id=transfer.id,
                       transfer_type_id=transfer_type.id)


def _get_account(user):
    # TODO: catch doesnotexist?
    try:
        return user.cc3_profile.cyclos_account
    except ObjectDoesNotExist:
        from cc3.cyclos.models import CyclosAccount
        return CyclosAccount.objects.get_for_user(user)


# DEPRECATING / NO LONGER USED
#def _get_user_for_system_account():
#    # TODO: impl mapping? or fake user instances?
#    cc3_bank_user = User.objects.get(pk=settings.CC3_BANK_USER_ID)
#    return cc3_bank_user


class PageableTransactions(object):
    def __init__(self, username=None, accounts=None, description=None,
                 from_to=None, from_date=None, to_date=None, direction='desc',
                 currency=None, account_type_id=None, custom_fields=None):
        self.username = username
        self.webservice = accounts
        self.total_count = None
        # search filters
        self.description = description
        self.from_to = from_to  # FIXME: *never* used.
        self.from_date = from_date
        self.to_date = to_date
        self.direction = direction
        self.currency = currency
        self.account_type_id = account_type_id
        self.custom_fields = custom_fields

    def __len__(self):
        return self.count()

    def __getitem__(self, k):
        # handle django template engine
        if k == u'count':
            return self.count()

        if isinstance(k, slice):
            start = k.start if k.start else 0
            stop = k.stop
            # convert to webservice 'paging' params
            page_size = stop - start
            if page_size > 0:
                current_page = start / page_size
            else:
                current_page = 0
            try:
                if self.username:
                    history = self.webservice.searchHistory(
                        principal=self.username,
                        pageSize=page_size,
                        currentPage=current_page,
                        beginDate=self.from_date,
                        endDate=self.to_date,
                        # Regular order is ascending (earliest first)
                        reverseOrder=(self.direction == 'desc'),
                        fields=self.custom_fields
                    )
                else:
                    history = self.webservice.searchMultipleHistories(
                        accountTypeId=self.account_type_id,
                        currency=self.currency,
                        pageSize=page_size,
                        currentPage=current_page,
                        beginDate=self.from_date,
                        endDate=self.to_date,
                        # Regular order is ascending (earliest first)
                        reverseOrder=(self.direction == 'desc'),
                        fields=self.custom_fields
                    )
                return [
                    _cyclos_transfer_to_transaction(transfer, self.username)
                    for transfer in history.transfers
                ]

            except (AccountNotFoundException, MemberNotFoundException):
                return None
        else:
            if self.username:
                try:
                    history = self.webservice.searchHistory(
                        principal=self.username,
                        pageSize=1,
                        currentPage=k,
                        beginDate=self.from_date,
                        endDate=self.to_date,
                        reverseOrder=(self.direction == 'desc'),
                        fields=self.custom_fields
                    )
                    single_transfer = history.transfers[0]
                    return _cyclos_transfer_to_transaction(
                        single_transfer, self.username)
                except (AccountNotFoundException, MemberNotFoundException):
                    return None
            else:
                # Not entirely sure this would ever be called.
                # Possibly at system start (ie when very few transactions?)
                history = self.webservice.searchMultipleHistories(
                    accountTypeId=self.account_type_id,
                    currency=self.currency,
                    pageSize=1,
                    currentPage=k,
                    beginDate=self.from_date,
                    endDate=self.to_date,
                    reverseOrder=(self.direction == 'desc'),
                    fields=self.custom_fields
                )
                single_transfer = history.transfers[0]

                return _cyclos_transfer_to_transaction(
                    single_transfer, self.username)

    def count(self):
        # NB this is never called - as the __getitem__ definition above is
        # called instead. (SDW: Not sure this is true - why do __len__ and
        # the __getitem__ called count()? )
        # If it is true, then is _resolve_count ever called ?
        if not self.total_count:
            self.total_count = self._resolve_count()
        return self.total_count

    def _resolve_count(self):

        # TODO: check for already resolved transaction list?
        if self.username:
            account_history = self.webservice.searchHistory(
                principal=self.username,
                principalType='USER',
                currentPage=0,
                pageSize=0,
                beginDate=self.from_date,
                endDate=self.to_date,
                reverseOrder=(self.direction == 'asc'),
                fields=self.custom_fields)
        else:
            account_history = self.webservice.searchMultipleHistories(
                accountTypeId=self.account_type_id,
                currency=self.currency,
                pageSize=0,
                currentPage=0,
                beginDate=self.from_date,
                endDate=self.to_date,
                reverseOrder=(self.direction == 'asc'),
                fields=self.custom_fields)

        return account_history.totalCount


#def _get_description(transfer):
#    """Try to extract a description from a returned Transfer instance"""
#    # For now this uses a custom field
#    # TODO: fix Cyclos webservice, add proper description field
#    if transfer.fields:
#        for field in transfer.fields:
#            if field.name == u'beschrijving':
#                return field.value
#    return None


def _get_custom_payment_fields(cc3_request, description):
    custom_fields = _get_optional_description_fields(description)
    if cc3_request is not None:
        cc3_field_value = u'cc3-{}'.format(cc3_request.id)
        custom_fields.append({u'field': u'cc3', u'value': cc3_field_value})
    return custom_fields


def _get_custom_fields(field_dictionary):
    custom_fields = []
    for key, value in field_dictionary.items():
        custom_fields.append({u'field': u"%s" % key,
                              u'value': u"%s" % value})
    return custom_fields


def _get_custom_donation_fields(description):
    custom_fields = _get_optional_description_fields(description)
    custom_fields.append({u'field': u'cc3', u'value': 'donation'})
    return custom_fields


def _get_custom_system_donation_fields(donation, description):
    custom_fields = _get_optional_description_fields(description)
    if donation is not None:
        cc3_field_value = u'incentive-{}'.format(donation.label)
        custom_fields.append({u'field': u'cc3',
                              u'value': cc3_field_value})
    return custom_fields


def _get_optional_description_fields(description):
    custom_fields = []
    if description is not None:
        custom_fields.append({u'field': u'beschrijving', u'value': description})
    return custom_fields


def _generate_dummy_password():
    return uuid4().hex[:12]


def _generate_dummy_pin():
    return '{:04d}'.format(random.randrange(9999))
