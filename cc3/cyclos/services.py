"""Cyclos (cyclos.org) (SOAP) webservices

Wrapping the Cyclos SOAP webservices.
Hiding all the SOAP client implementation details.

The cyclos webservice documentation doesn't seem to match the WSDl.
So base this Python 'API' on the WSDL.

But the WSDL has basically every parameters as 'optional' (minOccurs="0") and
specified as a string.
So we make up our own 'required' parameters and formats by trail-and-error

SOAP client responses are converted to specific response classes, hiding
SOAP client implementation details and act as documentation of the available
properties.

"""
import base64
import datetime
import iso8601
import logging
import os
import tempfile
import textwrap
from collections import namedtuple
from pprint import pprint
from string import ascii_letters, digits

from django.conf import settings
from django.core.mail import mail_admins

from pysimplesoap import simplexml
from pysimplesoap.client import SoapClient, SoapFault, soap_namespaces
from pysimplesoap.simplexml import SimpleXMLElement

from .common import AccountHistory, AccountStatus, NewMember

LOG = logging.getLogger(__name__)


# Workaround timezone parsing ('Z')
# TODO: send issue and patch upstream
simplexml.TYPE_UNMARSHAL_FN[datetime.datetime] = iso8601.parse_date

# cyclos exposes the wsdl files at:
#
# http://<cyclos>/cyclos/services/account?wsdl
# ie:
# http://10.211.55.13:8080/cyclos/services/account?wsdl
#
# replace account with other services below

MEMBER_PATH = '/services/members'
ACCESS_PATH = '/services/access'
ACCOUNT_PATH = '/services/account'
PAYMENT_PATH = '/services/payment'
POS_PATH = '/services/pos'
WSDL_MEMBER = '/services/members?wsdl'
WSDL_ACCESS = '/services/access?wsdl'
WSDL_ACCOUNT = '/services/account?wsdl'
# WSDL_FIELD = '/services/fields?wsdl'
WSDL_PAYMENT = '/services/payment?wsdl'
WSDL_POS = '/services/pos?wsdl'


def _to_local_file_url(path):
    file_path_to_return = 'file:{0}'.format(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), path))

    return file_path_to_return

WSDL_MEMBER_LOCAL = _to_local_file_url('wsdl/members.wsdl')
WSDL_ACCESS_LOCAL = _to_local_file_url('wsdl/access.wsdl')
WSDL_ACCOUNT_LOCAL = _to_local_file_url('wsdl/account.wsdl')
WSDL_PAYMENT_LOCAL = _to_local_file_url('wsdl/payment.wsdl')

NAMESPACE_PREFIX = 'cyclos'


class MemberNotFoundException(Exception):
    pass


class AccountNotFoundException(Exception):
    pass


class CyclosSoapClient(SoapClient):
    """
    Extends/tweak/patch SoapClient for use with Cyclos webservice.
    """
    def __init__(self, location=None, *args, **kwargs):
        LOG.debug('Initializing client with location {0}'.format(location))

        super(CyclosSoapClient, self).__init__(*args, **kwargs)
        self.basic_auth_enabled = False
        self.basic_auth_obfuscated = None
        self.response = None
        self.content = None

    def enable_http_basic_auth(self, basic_auth_user, basic_auth_pass):
        self.basic_auth_enabled = True
        self.basic_auth_obfuscated = base64.standard_b64encode(
            '{0}:{1}'.format(basic_auth_user, basic_auth_pass))

    # override
    def send(self, method, xml):
        """
        Send SOAP request using HTTP
        """
        if self.location == 'test':
            return

        location = '{0}'.format(self.location)
        # ?op=%s" % (self.location, method)

        if self.services:
            soap_action = self.action
        else:
            soap_action = self.action + method

        headers = {
            'Content-type': 'text/xml; charset="UTF-8"',
            'Content-length': str(len(xml)),
            'SOAPAction': '"{0}"'.format(soap_action)
        }
        # log.info("POST %s" % location)

        # add optional HTTP BASIC_AUTH
        if self.basic_auth_enabled:
            headers['Authorization'] = 'Basic {0}'.format(
                self.basic_auth_obfuscated)

        if self.trace:
            print '-' * 80
            print 'POST {0}'.format(location)
            print '\n'.join([
                  '{0}: {1}'.format(k, v) for k, v in headers.items()])
            print u'\n{0}'.format(xml.decode('utf8', 'ignore'))
        response, content = self.http.request(
            location, 'POST', body=xml, headers=headers)

        self.response = response
        self.content = content

        if self.trace:
            print '\n'.join([
                  '{0}: {1}'.format(k, v) for k, v in response.items()])
            print content
            # .decode("utf8","ignore")
            print '=' * 80

        return content


class BaseService(object):
    """Base class for the SOAP webservice `ports`"""
    service_location = None  # relative path of the webservice
    wsdl = None

    def __init__(self, base_location, basic_auth_user=None,
                 basic_auth_pass=None, trace=False, cache=False):
        if self.service_location is None:
            raise ValueError('Webservice location required')
        if self.wsdl is None:
            raise ValueError('WSDL location required')

        self.location = base_location + self.service_location
        self.cache = cache
        self.trace = trace
        self.basic_auth_user = basic_auth_user
        self.basic_auth_pass = basic_auth_pass

        LOG.debug('Initializing webservice for {0} on {1}'.format(
            self.wsdl, self.location))

    def get_client(self):
        client = CyclosSoapClient(
            location=self.location, wsdl=self.wsdl, ns=NAMESPACE_PREFIX,
            cache=_get_cache_dir(self.cache), trace=self.trace)

        if self.basic_auth_user is not None and \
                self.basic_auth_pass is not None:
            client.enable_http_basic_auth(self.basic_auth_user,
                                          self.basic_auth_pass)
        # override location set by wsdl
        if not(self.wsdl.startswith(self.location)):
            for service in client.services.values():
                for port in service['ports'].values():
                    port['location'] = self.location

        return client

    @property
    def client(self):
        # SoapClient is not thread safe, so new instance
        return self.get_client()


class Members(BaseService):
    """Cyclos member webservice"""
    service_location = MEMBER_PATH
    wsdl = WSDL_MEMBER_LOCAL

    def register(self, username, name, email, login_password=None,
                 credentials=None, group_id=None, pin=None, fields=None):
        """Register a new member

        login_password    max 12 characters
        pin               max 4 charsf
        """
        # just alphas - cyclos doesn't like hyphens for example
        username = ''.join([ch for ch in username if ch in (
            ascii_letters + digits)])

        # 'required' params
        params = {
            u'username': username,
            u'name': name,
            u'email': email,
            u'loginPassword': login_password
        }
        # optional parameters
        if login_password:
            params[u'loginPassword'] = login_password
        if credentials:
            params[u'credentials'] = credentials
        if group_id:
            params[u'groupId'] = group_id
        if pin:
            params[u'pin'] = pin
        # use the custom fields code below - can't marshall easily
#        if fields:
#            params[u'fields'] = fields

        xml_params = SimpleXMLElement('<dummyroot><params/></dummyroot>')
        for name, value in params.items():
            xml_params.params.marshall(name, value)

        if fields:
            for customField in fields:
                xml_params.params.marshall('fields', customField)

        client = self.get_client()
        operation = client.get_operation('registerMember')
        output = operation['output']

        soap_uri = soap_namespaces['soap']
        soap_response = client.call('registerMember', xml_params)
        # call returns a SimpleXMLElement,
        # send (see below) returns raw text XML
#        response_xml = SimpleXMLElement(soap_response)
        response_dict = soap_response(
            'Body', ns=soap_uri).children().unmarshall(output)
        response = response_dict and response_dict.values()[0]
        # pass Response tag children
        _log_response(response)

        # simpler version - but had to use above due to XML fields tricksiness
#        client = self.get_client()
#        response = client.registerMember(params=[params])
#        _log_response(response)
        returned = response['return']

        _id = returned.get('id', None)
        username = returned.get('username', None)
        awaiting_email_validation = returned.get(
            'awaitingEmailValidation', None)

        return NewMember(
            id=_id, username=username,
            awaitingEmailValidation=awaiting_email_validation)

    def update(self, _id, name=None, email=None, fields=None,
               principal=None, principalType=None):
        """Update an existing member"""
        params = {u'id': _id}
        if name:
            params[u'name'] = name
        if email:
            params[u'email'] = email
        # use the custom fields code below - can't marshall easily
#        if fields:
#            params[u'fields'] = fields
        if principal:
            params[u'principal'] = principal
        if principalType:
            params[u'principalType'] = principalType

        xml_params = SimpleXMLElement('<dummyroot><params/></dummyroot>')
        for name, value in params.items():
            xml_params.params.marshall(name, value)

        if fields:
            for customField in fields:
                xml_params.params.marshall('fields', customField)

        client = self.get_client()
        client.get_operation('updateMember')
        client.call('updateMember', xml_params)

        # simpler version - but had to use above due to XML fields tricksiness
#        client = self.get_client()
#        client.updateMember(params=[params])
        # updateMember: 'There is no explicit result'

    def updateGroup(self, _id, _groupId, _comments):
        """
        <xs:complexType name="updateMemberGroup">
            <xs:sequence>
                <xs:element minOccurs="0" name="params"
                type="tns:updateMemberGroupParameters"/>
            </xs:sequence>
        </xs:complexType>
            <xs:complexType name="updateMemberGroupParameters">
            <xs:sequence>
                <xs:element minOccurs="0" name="id" type="xs:long"/>
                <xs:element minOccurs="0" name="groupId" type="xs:long"/>
                <xs:element minOccurs="0" name="comments" type="xs:string"/>
            </xs:sequence>
        </xs:complexType>

        Update an existing members group
        """

        params = {u'id': _id, u'groupId': _groupId, u'comments': _comments}

        xml_params = SimpleXMLElement('<dummyroot><params/></dummyroot>')
        for name, value in params.items():
            xml_params.params.marshall(name, value)

#        if fields:
#            for customField in fields:
#                xml_params.params.marshall('fields', customField)
#
        client = self.get_client()
        operation = client.get_operation('updateMemberGroup')
#
        soap_uri = soap_namespaces['soap']
        soap_response = client.call('updateMemberGroup', xml_params)

#        # simpler version - but had to use above due to XML fields tricksiness
#        client = self.get_client()
#        client.updateMemberGroup(params=[params])
        # updateMemberGroup: 'There is no explicit result'

    def listManagedGroups(self):
        """Lists the groups managed by the current web service client."""
        # response = self.client.listManagedGroups()
        # Manual call, woraround no-param/empty senquence type
        client = self.get_client()
        operation = client.get_operation('listManagedGroups')
        output = operation['output']
        soap_uri = soap_namespaces['soap']

        soap_request = textwrap.dedent("""
        <soapenv:Envelope
                xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:mem="http://members.webservices.cyclos.strohalm.nl/">
           <soapenv:Header/>
           <soapenv:Body>
              <mem:listManagedGroups/>
           </soapenv:Body>
        </soapenv:Envelope>""")

        soap_response = client.send('listManagedGroups', soap_request)
        # Now mimic the 'wsdl'-based output conversion
        response_xml = SimpleXMLElement(soap_response)
        response_dict = response_xml(
            'Body', ns=soap_uri).children().unmarshall(output)
        response = response_dict and response_dict.values()[0]
        # pass Response tag children
        _log_response(response)
        return [MemberGroup(**response_item['return'])
                for response_item in response]

    def fullTextSearch(self, currentPage=None, pageSize=None, keywords=None,
                       email=None, groupIds=None, groupFilterIds=None,
                       fields=None, showCustomFields=False, showImages=None):
        """
        fullTextSearch: Searches for members using a full text search
        technique, which is best suited when the user supplies keywords. The
        results are ordered by relevance, listing the best results first.

        :param currentPage: The current query page, starting at zero.
            Defaults to 0.
        :param pageSize: The number of records per page. Defaults to 10.
        :param keywords: Keywords to search.
        :param email: The email to search. NB SW: CYCLOS hasn't implemented
            this in 3.6.1!
        :param groupIds: An array of group identifiers.
        :param groupFilterIds: An array of group filter identifiers.
        :param fields: The custom field values for the
            member. Each fieldValue contains the field internal name and the
            value. When searching for an enumerated field, the value must be
            the possible value id.
        :param showCustomFields: Indicates if the custom fields will
            be retrieved together with each member. Defaults to False.
        :param showImages: Indicates if the images information will be
            retrieved together with each member. Defaults to false.
        :return: A page of members, containing the following attributes:
            * currentPage (integer): The current page in the search.
            * totalCount (integer): The total number of members (not only those
              returned in the page).
            * ads (array of member): Contains the details for each member. For
              more details, refer to the model data details

        Fault codes:
            query-parse-error: When the given keywords contains an invalid
            expression.
        """
        import xml.dom.minidom

        # 'required' params
        params = {}
        if currentPage:
            params['currentPage'] = currentPage
        if pageSize:
            params['pageSize'] = pageSize
        if keywords:
            params['keywords'] = keywords
        if email:
            params['email'] = email
        if groupIds:
            params['groupIds'] = groupIds
        if groupFilterIds:
            params['groupFilterIds'] = groupFilterIds
        if fields:
            params['fields'] = fields
        if showCustomFields:
            params['showCustomFields'] = showCustomFields
        if showImages:
            params['showImages'] = showImages

        # this fails to make a list of the members
        # (the XML unmarshalling gets the last member in the list
        # only due to XML design)
#        response = self.client.fullTextSearch(params=params)

        # use the more manual technique as seen in 'doPayment',
        # and parse the response here for our purposes
        client = self.get_client()
        operation = client.get_operation('fullTextSearch')
        soap_uri = soap_namespaces['soap']
        xml_params = SimpleXMLElement('<dummyroot><params/></dummyroot>')
        for name, value in params.items():
            xml_params.params.marshall(name, value)

        soap_response = client.call('fullTextSearch', xml_params)
        body_children = soap_response('Body', ns=soap_uri).children()
        members_dom = xml.dom.minidom.parseString(body_children.as_xml())
        members_list_dom = members_dom.getElementsByTagName('members')
        members = []
        for member in members_list_dom:
            id = (int)(self.getText(
                member.getElementsByTagName('id')[0].childNodes))
            name = self.getText(
                member.getElementsByTagName('name')[0].childNodes)
            email = self.getText(
                member.getElementsByTagName('email')[0].childNodes)
            username = self.getText(
                member.getElementsByTagName('username')[0].childNodes)
            members.append((id, name, email, username))

        return members

    def search(self, currentPage=None, pageSize=None, username=None, name=None,
               email=None, randomOrder=False, groupIds=None,
               groupFilterIds=None, fields=None, showCustomFields=None,
               showImages=None ):
        """
        Searches for members, returning a page of members.

        :param currentPage:
        :param pageSize:
        :param username: A text to search within the login name.
        :param name: A text to search within the name.
        :param email:
        :param randomOrder: When set to true, the result order will be
            scrambled.
        :param groupIds:
        :param groupFilterIds:
        :param fields:
        :param showCustomFields:
        :param showImages:
        :return: A page of members, containing the following attributes:
            * currentPage (integer): The current page in the search.
            * totalCount (integer): The total number of members (not only those
              returned in the page).
            * ads (array of member): Contains the details for each member. For
              more details, refer to the model data details.

        Fault codes:
            query-parse-error: When the given keywords contains an invalid
            expression.
        """
        import xml.dom.minidom

        # 'required' params
        params = {}
        if currentPage:
            params['currentPage'] = currentPage
        if pageSize:
            params['pageSize'] = pageSize
        if username:
            params['username'] = username
        if email:
            params['email'] = email
        if name:
            params['name'] = name
        if randomOrder:
            params['randomOrder'] = randomOrder
        if groupIds:
            params['groupIds'] = groupIds
        if groupFilterIds:
            params['groupFilterIds'] = groupFilterIds
        if fields:
            params['fields'] = fields
        if showCustomFields:
            params['showCustomFields'] = showCustomFields
        if showImages:
            params['showImages'] = showImages

        # this fails to make a list of the members
        # (the XML unmarshalling gets the last member in the list only due to
        # XML design)
#        response = self.client.fullTextSearch(params=params)

        # use the more manual technique as seen in 'doPayment',
        # and parse the response here for our purposes
        client = self.get_client()
        operation = client.get_operation('search')
        soap_uri = soap_namespaces['soap']
        xml_params = SimpleXMLElement('<dummyroot><params/></dummyroot>')
        for name, value in params.items():
            xml_params.params.marshall(name, value)

        soap_response = client.call('search', xml_params)
        body_children = soap_response('Body', ns=soap_uri).children()

        members_dom = xml.dom.minidom.parseString(body_children.as_xml())
        members_list_dom = members_dom.getElementsByTagName('members')
        members = []
        for member in members_list_dom:
            id = (int)(self.getText(
                member.getElementsByTagName('id')[0].childNodes))
            name = self.getText(
                member.getElementsByTagName('name')[0].childNodes)
            email = self.getText(
                member.getElementsByTagName('email')[0].childNodes)
            username = self.getText(
                member.getElementsByTagName('username')[0].childNodes)
            groupId = self.getText(
                member.getElementsByTagName('groupId')[0].childNodes)
            members.append((id, name, email, username, groupId))

        return members

    def getText(self, nodelist):
        """
        Utility method for grabbing text from a minidom XML node
         - http://docs.python.org/library/xml.dom.minidom.html#dom-objects
        """
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)


class Payments(BaseService):
    """Cyclos payment webservice"""
    service_location = PAYMENT_PATH
    wsdl = WSDL_PAYMENT_LOCAL

    def doPayment(self, amount, fromMemberPrincipalType=None, fromMember=None,
                  fromSystem=None, toMemberPrincipalType=None, toMember=None,
                  toSystem=None, currency=None, credentials=None,
                  description=None, transferTypeId=None,
                  fromMemberFieldsToReturn=None, toMemberFieldsToReturn=None,
                  traceNumber=None, customValues=None):
        """perform a single payment"""
        params = {u'amount': amount}
        if fromMemberPrincipalType is not None:
            params[u'fromMemberPrincipalType'] = fromMemberPrincipalType
        if fromMember is not None:
            params[u'fromMember'] = fromMember
        if fromSystem is not None:
            params[u'fromSystem'] = 'true' if fromSystem else 'false'
        if toMemberPrincipalType is not None:
            params[u'toMemberPrincipalType'] = toMemberPrincipalType
        if toMember is not None:
            params[u'toMember'] = toMember
        if toSystem is not None:
            params[u'toSystem'] = 'true' if toSystem else 'false'
        if currency is not None:
            params[u'currency'] = currency
        if credentials is not None:
            params[u'credentials'] = credentials
        if description is not None:
            params[u'description'] = description
        if transferTypeId is not None:
            params[u'transferTypeId'] = transferTypeId
        if fromMemberFieldsToReturn is not None:
            params[u'fromMemberFieldsToReturn'] = fromMemberFieldsToReturn
        if toMemberFieldsToReturn is not None:
            params[u'toMemberFieldsToReturn'] = toMemberFieldsToReturn
        if traceNumber is not None:
            params[u'traceNumber'] = traceNumber

        # `manual` XML serializing/mashalling
        # customValues is a xml 'list' elements without a wrapper

        xml_params = SimpleXMLElement('<dummyroot><params/></dummyroot>')
        for name, value in params.items():
            xml_params.params.marshall(name, value)

        if customValues is not None:
            for customValue in customValues:
                xml_params.params.marshall('customValues', customValue)

        client = self.get_client()
        operation = client.get_operation('doPayment')
        output = operation['output']
        soap_uri = soap_namespaces['soap']

        try:
            soap_response = client.call('doPayment', xml_params)
        except Exception, e:
            # Log any exception with the used XML parameters.
            data = []
            for key, value in params.items():
                data.append(u'{0}: {1}'.format(key, value))

            data = '\n'.join(data)

            message = u'SOAP request failed - {0}\n\n-- XML params:\n' \
                      u'{1}'.format(e, data)
            LOG.error(message)

            if not settings.DEBUG:
                mail_admins(u'Payment failed', message, fail_silently=True)

            # Now return an invalid ``Payment`` status.
            return Payment(Payment.STATUS_UNKNOWN_ERROR, None)

        response_dict = soap_response(
            'Body', ns=soap_uri).children().unmarshall(output)
        response = response_dict and response_dict.values()[0]
        # pass Response tag children
        _log_response(response)
        return _convert_payment_response(response)


class Accounts(BaseService):
    """Cyclos account webservice"""
    service_location = ACCOUNT_PATH
    wsdl = WSDL_ACCOUNT_LOCAL

    def searchHistory(self, principal, principalType=None, currentPage=None,
                      pageSize=None, credentials=None, accountTypeId=None,
                      currency=None, relatedMemberPrincipalType=None,
                      relatedMember=None, beginDate=None, endDate=None,
                      fields=None, reverseOrder=None):
        """get accounts status and search transfer history"""
        # we always need a principal
        params = {u'principal': principal}
        # other optional params
        if principalType is not None:
            params[u'principalType'] = principalType
        if pageSize is not None:
            params[u'pageSize'] = pageSize
        if currentPage is not None and currentPage !=u'count':
            params[u'currentPage'] = currentPage
        if credentials is not None:
            params[u'credentials'] = credentials
        if accountTypeId is not None:
            params[u'accountTypeId'] = accountTypeId
        if currency is not None:
            params[u'currency'] = currency
        if relatedMember is not None:
            params[u'relatedMember'] = relatedMember
        if relatedMemberPrincipalType is not None:
            params[u'relatedMemberPrincipalType'] = relatedMemberPrincipalType
        if beginDate is not None:
            params[u'beginDate'] = beginDate
        if endDate is not None:
            params[u'endDate'] = endDate
        if fields is not None:
            params[u'fields'] = fields
        if reverseOrder is not None:
            params[u'reverseOrder'] = 'true' if reverseOrder else 'false'

        client = self.get_client()
        try:
            response = client.searchAccountHistory(params=params)
        except SoapFault as soap_fault:
            #TODO: handle fault namespace in code (ns1:xxxxxx)
            if 'member-not-found' in soap_fault.faultcode:
                raise MemberNotFoundException(
                    'Member {} not found'.format(principal))
            elif 'specified account was not found' in \
                    soap_fault.faultstring.lower():
                raise AccountNotFoundException(
                    'Account {} not found'.format(principal))
            else:
                # re-raise soap fault
                raise
        _log_response(response)
        returned = response['return']
        accountStatus = None
        transfers = []
        currentPage = totalCount = None

        if isinstance(returned, dict):  # type(returned)== type({}):
            currentPage = returned['currentPage']
            totalCount = returned['totalCount']
            accountStatus = AccountStatus(**returned['accountStatus'])
            if 'transfers' in returned:

                transfers.append(_convert_transfer(returned['transfers']))
        else:
            for response_element in returned:
                if 'currentPage' in response_element:
                    currentPage = response_element['currentPage']
                elif 'totalCount' in response_element:
                    totalCount = response_element['totalCount']
                elif 'accountStatus' in response_element:
                    # for some reason cyclos doesn't always return these keys
                    # add to avoid upsetting AccountStatus tuple creation
                    if not 'upperCreditLimit' in \
                            response_element['accountStatus']:
                        response_element['accountStatus']['upperCreditLimit'] = None
                    if not 'formattedUpperCreditLimit' in response_element['accountStatus']:
                        response_element['accountStatus']['formattedUpperCreditLimit'] = None

                    accountStatus = AccountStatus(
                        **response_element['accountStatus'])
                elif 'transfers' in response_element:
                    transfers.append(
                        _convert_transfer(response_element['transfers']))
#        for t in transfers:
#            if t.member:
#                print t.member.name
#        print [t.member.name for t in transfers]
        return AccountHistory(accountStatus=accountStatus,
                              currentPage=currentPage,
                              totalCount=totalCount,
                              transfers=transfers)

    def searchMultipleHistories(self, principal=None, principalType=None,
                                currentPage=None, pageSize=None,
                                credentials=None,
                                accountTypeId=None, currency=None,
                                relatedMemberPrincipalType=None,
                                relatedMember=None,
                                beginDate=None, endDate=None,
                                fields=None, reverseOrder=None):
        """get accounts status and search transfer history"""
        # No principal - multiple accounts... but wsdl requires. it's ignored
        params = {u'principal': ''}
        # other optional params
        if principalType is not None:
            params[u'principalType'] = principalType
        if pageSize is not None:
            params[u'pageSize'] = pageSize
        if currentPage is not None and currentPage != u'count':
            params[u'currentPage'] = currentPage
        if credentials is not None:
            params[u'credentials'] = credentials
        if accountTypeId is not None:
            params[u'accountTypeId'] = accountTypeId
        if currency is not None:
            params[u'currency'] = currency
        if relatedMember is not None:
            params[u'relatedMember'] = relatedMember
        if relatedMemberPrincipalType is not None:
            params[u'relatedMemberPrincipalType'] = relatedMemberPrincipalType
        if beginDate is not None:
            params[u'beginDate'] = beginDate
        if endDate is not None:
            params[u'endDate'] = endDate
        if fields is not None:
            params[u'fields'] = fields
        if reverseOrder is not None:
            params[u'reverseOrder'] = 'true' if reverseOrder else 'false'

        client = self.get_client()
        try:
            response = client.searchMultipleAccountHistories(params=params)
        except SoapFault as soap_fault:
            #TODO: handle fault namespace in code (ns1:xxxxxx)
            if 'member-not-found' in soap_fault.faultcode:
                raise MemberNotFoundException(
                    'Member {} not found'.format(principal))
            elif 'specified account was not found' in \
                    soap_fault.faultstring.lower():
                raise AccountNotFoundException(
                    'Account {} not found'.format(principal))
            else:
                raise  # re-raise soap fault
        _log_response(response)
        returned = response['return']
        accountStatus = None
        transfers = []
        currentPage = totalCount = None

        if isinstance(returned, dict):  # type() == type({}):
            currentPage = returned['currentPage']
            totalCount = returned['totalCount']
            accountStatus = AccountStatus(**returned['accountStatus'])
            if 'transfers' in returned:

                transfers.append(_convert_transfer(returned['transfers']))
        else:
            for response_element in returned:
                if 'currentPage' in response_element:
                    currentPage = response_element['currentPage']
                elif 'totalCount' in response_element:
                    totalCount = response_element['totalCount']
                elif 'accountStatus' in response_element:
                    # for some reason cyclos doesn't always return these keys
                    # add to avoid upsetting AccountStatus tuple creation
                    # TODO check the WSDL - some commenting was necessary from
                    # the WSDL generated by cyclos
                    if not 'upperCreditLimit' in response_element['accountStatus']:
                        response_element['accountStatus']['upperCreditLimit'] = None
                    if not 'formattedUpperCreditLimit' in response_element['accountStatus']:
                        response_element['accountStatus']['formattedUpperCreditLimit'] = None

                    accountStatus = AccountStatus(**response_element['accountStatus'])
                elif 'transfers' in response_element:
                    transfers.append(_convert_transfer(
                        response_element['transfers']))
#        for t in transfers:
#            if t.member:
#                print t.member.name
#        print [t.member.name for t in transfers]
        return AccountHistory(accountStatus=accountStatus,
                              currentPage=currentPage,
                              totalCount=totalCount,
                              transfers=transfers)

    def getMemberAccounts(self, principal, principalType=None):
        params = {u'principal': principal}
        if principalType is not None:
            params[u'principalType'] = principalType
        response = self.client.getMemberAccounts(params=params)
        _log_response(response)
        return [response_item['return'] for response_item in response]

    def search_transfer_types(
            self, currency=None, from_member_principal_type=None,
            from_member=None, to_member_principal__type=None, to_member=None,
            to_system=None, from_system=None, from_account_type_id=None,
            to_account_type_id=None):
        params = {}
        if currency is not None:
            params[u'currency'] = currency
        if from_member_principal_type is not None:
            params[u'fromMemberPrincipalType'] = from_member_principal_type
        if from_member is not None:
            params[u'fromMember'] = from_member
        if to_member_principal__type is not None:
            params[u'toMemberPrincipalType'] = to_member_principal__type
        if to_member is not None:
            params[u'toMember'] = to_member
        if to_system is not None:
            params[u'toSystem'] = to_system
        if from_system is not None:
            params[u'fromSystem'] = from_system
        if from_account_type_id is not None:
            params[u'fromAccountTypeId'] = from_account_type_id
        if to_account_type_id is not None:
            params[u'toAccountTypeId'] = to_account_type_id

        client = self.get_client()
        response = client.searchTransferTypes(params=params)
        _log_response(response)
        return [_convert_transferType(response_item['return']) for
                response_item in response]


class Access(BaseService):
    """Cyclos access webservice"""
    service_location = ACCESS_PATH
    wsdl = WSDL_ACCESS_LOCAL

    def isChannelEnabledForMember(self, principal, principalType=None):
        params = {u'principal': principal}
        if principalType is not None:
            params[u'principalType'] = principalType

        response = self.client.isChannelEnabledForMember(params=params)
        _log_response(response)
        return response['return']

    def checkChannel(self, principal, channel_internal_name,
                     principalType=None):
        params = {u'principal': principal}
        if principalType is not None:
            params[u'principalType'] = principalType
        params[u'channel'] = channel_internal_name

        response = self.client.checkChannel(params=params)
        _log_response(response)
        return response['return']

    def changeChannels(self, principal, channels,
                       principalType=None):
        params = {u'principal': principal}
        if principalType is not None:
            params[u'principalType'] = principalType

        xml_params = SimpleXMLElement('<dummyroot><params/></dummyroot>')
        for name, value in params.items():
            xml_params.params.marshall(name, value)

        changeChannelsParameters = []
        for internal_name, channel_enabled in channels.items():
            enabled = '0'
            if channel_enabled:
                enabled = '1'

            changeChannelsParameters.append({u'channel': internal_name,
                                             u'enabled': enabled})

        for changeChannelParameters in changeChannelsParameters:
            xml_params.params.marshall('channels',
                                       changeChannelParameters)

        client = self.get_client()
        operation = client.get_operation('changeChannels')
        output = operation['output']
        soap_uri = soap_namespaces['soap']

        soap_response = client.call('changeChannels', xml_params)

        _log_response(soap_response)

        return soap_response['return']


# Webservice response classes
# TODO: probably need to re-implement/extend these with 'optional' properties
#       instead of 'prototype'/._replace method

#{
#    'balance': Decimal('1000.000000'),
#    'formattedBalance': u'1.000 CC',
#    'availableBalance': Decimal('1000.000000'),
#    'formattedAvailableBalance': u'1.000 CC',
#    'reservedAmount': Decimal('0'),
#    'formattedReservedAmount': u'0 CC',
#    'creditLimit': Decimal('0.000000'),
#    'formattedCreditLimit': u'0 CC',
#   }

class Payment(namedtuple('Payment', ['status', 'transfer'])):
    """
    ``namedtuple`` subclass with included payment status definitions.
    """
    STATUS_PROCESSED = 'PROCESSED'
    STATUS_PENDING_AUTHORIZATION = 'PENDING_AUTHORIZATION'
    STATUS_INVALID_CREDENTIALS = 'INVALID_CREDENTIALS'
    STATUS_BLOCKED_CREDENTIALS = 'BLOCKED_CREDENTIALS'
    STATUS_INVALID_CHANNEL = 'INVALID_CHANNEL'
    STATUS_INVALID_PARAMETERS = 'INVALID_PARAMETERS'
    STATUS_FROM_NOT_FOUND = 'FROM_NOT_FOUND'
    STATUS_TO_NOT_FOUND = 'TO_NOT_FOUND'
    STATUS_NOT_ENOUGH_CREDITS = 'NOT_ENOUGH_CREDITS'
    STATUS_MAX_DAILY_AMOUNT_EXCEEDED = 'MAX_DAILY_AMOUNT_EXCEEDED'
    STATUS_RECEIVER_UPPER_CREDIT_LIMIT_REACHED = \
        'RECEIVER_UPPER_CREDIT_LIMIT_REACHED'
    STATUS_NOT_PERFORMED = 'NOT_PERFORMED'
    STATUS_UNKNOWN_ERROR = 'UNKNOWN_ERROR'


Transfer = namedtuple('Transfer', ['id',
                                   'transferType',
                                   'fromMember',
                                   'member',
                                   'amount', 'formattedAmount',
                                   'date', 'formattedDate',
                                   'processDate', 'formattedProcessDate',
                                   'systemAccountName',
                                   'fromSystemAccountName', 'description',
                                   'fields', 'transactionNumber',
                                   'status'
                                   ])


transfer_prototype = Transfer(*(None,) * len(Transfer._fields))


TransferType = namedtuple('TransferType', ['id', 'name', 'from_', 'to'])
TransferTypeTarget = namedtuple('TransferTypeTarget', ['id', 'name',
                                                       'currency'])
Member = namedtuple('Member', ['id', 'username', 'name', 'groupId', 'email'])
CustomField = namedtuple('CustomField', ['name', 'value'])
MemberGroup = namedtuple('MemberGroup', ['id', 'name'])


def _convert_payment_response(response):
    """Convert response from SOAP client to our response object"""
    returned = response['return']
    status = returned['status']
    if 'transfer' in returned:
        transfer = _convert_transfer(returned['transfer'])
    else:
        transfer = None
    return Payment(status, transfer)


def _convert_transfer(transfer_list):
    transferType = None
    member = None
    fields = []
    transfer_dict = {}

    if isinstance(transfer_list, dict):
        transferType = _convert_transferType(transfer_list['transferType'])
        member = None
        if 'member' in transfer_list:
            member = Member(**transfer_list['member'])
        if 'fields' in transfer_list:
            value = transfer_list['fields']
            field = CustomField(
                name=value['internalName'],
                value=value['value']
            )
            fields.append(field)
        transfer_dict = transfer_list
        if 'member' in transfer_list:
            transfer_list.pop('member')
        if 'fields' in transfer_list:
            transfer_list.pop('fields')
        transfer_list.pop('transferType')

    else:
        for el_dict in transfer_list:
            for key, value in el_dict.items():
                # a couple of 'custom' conversions
                if key == 'transferType':
                    transferType = _convert_transferType(value)
                elif key == 'member':
                    member = Member(**value)
                elif key == 'fields':
                    field = CustomField(
                        name=value['internalName'],
                        value=value['value']
                    )
                    fields.append(field)
                else:  # default conversion
                    transfer_dict[key] = value
    transfer = transfer_prototype._replace(transferType=transferType,
                                           member=member,
                                           fields=fields,
                                           **transfer_dict)
    return transfer


def _convert_transferType(transferType_dict):
    from_ = TransferTypeTarget(**transferType_dict['from'])
    to = TransferTypeTarget(**transferType_dict['to'])
    return TransferType(id=transferType_dict['id'],
                        name=transferType_dict['name'],
                        from_=from_,
                        to=to)


def _get_cache_dir(enabled):
    if not enabled:
        return False
    # TODO: impl better tmp dir location (from a settings propery?)
    path = os.path.join(tempfile.gettempdir(), 'cyclos-webservices')
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _log_response(response):
    if LOG.isEnabledFor(logging.DEBUG):
        LOG.debug(pprint(response))
