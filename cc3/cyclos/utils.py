import logging
from os import path as os_path

from django.conf import settings
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from cc3.cyclos import backends
from cc3.cyclos import dbaccess
from cc3.mail.models import MailMessage

from .sql.transfer import (
    TRANSFERS_SELECT,
    TRANSFERS_TOTALS_BY_SENDER, TRANSFERS_TOTALS_BY_RECIPIENT,
    TRANSFERS_WHERE_SENDER,
    TRANSFERS_WHERE_RECIPIENT, TRANSFERS_WHERE_SENDER_OR_RECIPIENT,
    TRANSFERS_WHERE_TYPE_ID, TRANSFERS_WHERE_FROM_DATE,
    TRANSFERS_WHERE_TO_DATE)

LOG = logging.getLogger('cc3.cyclos.utils')

def viewable_user_filter(fieldname='user'):
    kwargs = {'{}__is_active'.format(fieldname): True}
    return Q(**kwargs)


def check_cyclos_account(email_address):

    try:
        list_of_members_with_email = backends.search(email=email_address,)

        return_string = None
        if list_of_members_with_email:
            # NB could link django account with the existing Cyclos one
            # make configurable?
            return_string = mark_safe(
                _(u"There is already an account with this e-mail address in "
                  u"our system."))
    except Exception, e:
        logging.error(
            'Problem checking cyclos account exception {0} (at {1})'.format(
                e, settings.CYCLOS_URL))
        return_string = mark_safe(
            _(u"Cannot connect to check email in the backend system at the "
              u"moment, please try later."))
    return return_string


def check_cyclos_account_by_username(username):

    try:
        list_of_members_with_username = backends.search(username=username,)

        return_string = None
        if list_of_members_with_username:
            # NB could link django account with the existing Cyclos one
            # make configurable?
            return_string = mark_safe(
                _(u"There is already an account with this username in "
                  u"our system."))
    except Exception, e:
        logging.error(
            'Problem checking cyclos account exception {0} (at {1})'.format(
                e, settings.CYCLOS_URL))
        return_string = mark_safe(
            _(u"Cannot connect to check username in the backend system at the "
              u"moment, please try later."))
    return return_string


def get_profile_picture_filename(instance, filename):
    return os_path.join('profile_pictures', '{0}_{1}'.format(
        instance.id, filename))


def get_cyclos_channel_image_filename(instance, filename):
    return os_path.join('cyclos_channels', '{0}_{1}'.format(
        instance.id, filename))


def mail_community_admins(instance, mail_type, language, extra_context=None):
    try:
        msg = MailMessage.objects.get_msg(mail_type, lang=language)
    except MailMessage.DoesNotExist as e:
        LOG.warning('Not sending new user notifications: {0}'.format(e))
        return

    for comm_admin in instance.community.get_administrators():
        context = {'user_profile': instance}
        if extra_context:
            context.update(extra_context)
        try:
            msg.send(comm_admin.user.email, context)
        except Exception as e:
            # Widely catch every exception to avoid blocking the registration
            # process. Log it for maintenance.
            LOG.error('Not sending email to community admin {0}: '
                      '{1}'.format(comm_admin.pk, e))


def get_cyclos_connection():
    return dbaccess.get_cyclos_connection()


def close_cyclos_connection(conn):
    return dbaccess.close_cyclos_connection(conn)


def get_cyclos_transfers(conn, senders=None, recipients=None, involving=None,
                         transfer_type_ids=None, from_date=None, to_date=None):
    """Get filtered cyclos transfers from the cyclos database

    All args, if not None, are used to filter the transfers:
        ``senders``, ``recipients`` and ``involving`` are lists
            of usernames
        ``from_date``, ``to_date``
        ``transfer_type_ids``
    """
    select_sql = TRANSFERS_SELECT
    where_sql = ''
    where_clauses = []
    args = []
    if senders is not None:
        where_clauses.append(TRANSFERS_WHERE_SENDER)
        args.append(senders)
    if recipients is not None:
        where_clauses.append(TRANSFERS_WHERE_RECIPIENT)
        args.append(recipients)
    if involving is not None:
        where_clauses.append(TRANSFERS_WHERE_SENDER_OR_RECIPIENT)
        args.append(involving)
        args.append(involving)
    if transfer_type_ids is not None:
        where_clauses.append(TRANSFERS_WHERE_TYPE_ID)
        args.append(transfer_type_ids)
    if from_date is not None:
        where_clauses.append(TRANSFERS_WHERE_FROM_DATE)
        args.append(from_date)
    if to_date is not None:
        where_clauses.append(TRANSFERS_WHERE_TO_DATE)
        args.append(to_date)

    if where_clauses:
        where_sql = " WHERE {0}".format(" AND ".join(where_clauses))
    sql = "{0}{1};".format(select_sql, where_sql)

    for trans in dbaccess.cyclos_query_results(conn, sql, args):
        yield trans
    # TODO:
    # use a dummy model / namedtuple instead of dict ?


def get_cyclos_transfer_totals(
        conn, group_by=None, senders=None, recipients=None, involving=None,
        transfer_type_ids=None, from_date=None, to_date=None):
    """Get total amounts for filtered transfers from the cyclos database

    Transfers are filtered as described above. Returns total amount
    by sender, as a dict keyed by username. Overall total is keyed by "None"
    """
    if group_by == 'sender':
        query_sql = TRANSFERS_TOTALS_BY_SENDER
    elif group_by == 'recipient':
        query_sql = TRANSFERS_TOTALS_BY_RECIPIENT
    else:
        query_sql = "Not yet implemented"
    where_sql = ''
    where_clauses = []
    args = []
    if senders is not None:
        where_clauses.append(TRANSFERS_WHERE_SENDER)
        args.append(senders)
    if recipients is not None:
        where_clauses.append(TRANSFERS_WHERE_RECIPIENT)
        args.append(recipients)
    if involving is not None:
        where_clauses.append(TRANSFERS_WHERE_SENDER_OR_RECIPIENT)
        args.append(involving)
        args.append(involving)
    if transfer_type_ids is not None:
        where_clauses.append(TRANSFERS_WHERE_TYPE_ID)
        args.append(transfer_type_ids)
    if from_date is not None:
        where_clauses.append(TRANSFERS_WHERE_FROM_DATE)
        args.append(from_date)
    if to_date is not None:
        where_clauses.append(TRANSFERS_WHERE_TO_DATE)
        args.append(to_date)

    if where_clauses:
        where_sql = " WHERE {0}".format(" AND ".join(where_clauses))

    sql = query_sql.format(where_sql=where_sql) + ';'

    totals = {}
    for row in dbaccess.cyclos_query_results(conn, sql, args):
        key = row.get(group_by) or "_TOTAL_"
        totals[key] = row.get('total_amount')

    return totals


def is_consumer_member(user):
    if hasattr(user, 'cc3_profile') and user.cc3_profile is not None:
        return user.cc3_profile.cyclos_group.name in getattr(
                settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', ())
    else:
        return False

