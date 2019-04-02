from django.utils.datastructures import SortedDict


def dictfetchall(cursor):
    """Returns all rows from a cursor as a dict"""
    desc = cursor.description
    return [
        SortedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def run_custom_sql(_sql, _params):
    """
    https://docs.djangoproject.com/en/1.5/topics/db/sql/#executing-custom-sql-directly
    :return:
    """
    from django.db import connection
    cursor = connection.cursor()

    # Data retrieval operation - no commit required
    cursor.execute(_sql, _params)

    return dictfetchall(cursor)


def run_cyclos_sql(_sql, _params):
    from cc3.cyclos.dbaccess import (
        get_cyclos_connection, close_cyclos_connection, cyclos_query_results)
    conn = get_cyclos_connection(results_as_dict=False)

    cursor = conn['cursor']
    cursor.execute(_sql, _params)
    data = dictfetchall(cursor)
    #data = [row for row in cyclos_query_results(conn, _sql, _params)]
    close_cyclos_connection(conn)

    return data
