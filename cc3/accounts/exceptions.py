from rest_framework.exceptions import APIException


class APITransactionException(APIException):
    status_code = 500
    detail = "transaction_failed"
