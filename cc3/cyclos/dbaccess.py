"""Direct access to the Cyclos database"""

import logging
import MySQLdb
import MySQLdb.cursors

from django.conf import settings


LOG = logging.getLogger('__file__')


# These defaults work for the Vagrant setup
CYCLOS_DB_CONFIG = {
    'user': getattr(settings, "CYCLOS_DB_USER", 'cyclos3'),
    'passwd': getattr(settings, "CYCLOS_DB_PASSWD", 'cyclos3'),
    'host': getattr(settings, "CYCLOS_DB_HOST", '192.168.100.2'),
    'db': getattr(settings, "CYCLOS_DB", 'cyclos3'),
    #'cursorclass': MySQLdb.cursors.DictCursor,
}
ROWLIMIT = 1000


def get_cyclos_connection(results_as_dict=True):
    if results_as_dict:
        cursorclass = MySQLdb.cursors.DictCursor
    else:
        cursorclass = MySQLdb.cursors.Cursor
    db = MySQLdb.connect(**CYCLOS_DB_CONFIG)
    return {
        'db': db,
        'cursor': db.cursor(cursorclass)
    }


def close_cyclos_connection(connection):
    connection['cursor'].close()
    connection['db'].close()


def cyclos_query_results(connection, sql, args):
    try:
        connection['cursor'].execute(sql, args)
        while True:
            results = connection['cursor'].fetchmany(ROWLIMIT)
            LOG.debug("Fetched {0} results".format(len(results)))
            if not results:
                break
            for row in results:
                yield row
    except:
        LOG.error("Error executing SQL: {0}".format(connection['cursor']._last_executed))
        raise
