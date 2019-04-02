# pulled out of models.py to avoid circular imports
from django.utils.translation import ugettext_lazy as _


BILLING_PERIOD_ONEOFF = "ONEOFF"
BILLING_PERIOD_YEARLY = "YEARLY"
BILLING_PERIOD_MONTHLY = "MONTHLY"

BILLING_PERIODS = (
    (BILLING_PERIOD_ONEOFF, _('One-off')),
    (BILLING_PERIOD_YEARLY, _('Yearly')),
    (BILLING_PERIOD_MONTHLY, _('Monthly')),
)

AUTO_ASSIGN_TYPE_TERMINAL_DEPOSIT = "TERMINAL_DEPOSIT"
AUTO_ASSIGN_TYPE_TERMINAL_REFUND = "TERMINAL_REFUND"
AUTO_ASSIGN_TYPE_TERMINAL_RENTAL = "TERMINAL_RENTAL"
AUTO_ASSIGN_TYPE_SIM_CARD = "SIM_CARD"
AUTO_ASSIGN_TYPE_USER_GROUPS= "USER_GROUPS"
AUTO_ASSIGN_TYPE_TRANSACTIONS = "TRANSACTIONS"

AUTO_ASSIGN_TYPES = (
    (AUTO_ASSIGN_TYPE_TERMINAL_DEPOSIT,
        _('When terminal assigned to user')),
    (AUTO_ASSIGN_TYPE_TERMINAL_REFUND,
        _('When terminal unassigned from user')),
    (AUTO_ASSIGN_TYPE_TERMINAL_RENTAL,
        _('To all terminal holders (excl. free ones)')),
    (AUTO_ASSIGN_TYPE_SIM_CARD,
        _('To all SIM card holders')),
    (AUTO_ASSIGN_TYPE_USER_GROUPS,
        _("To all users in product's User Groups")),
    #(AUTO_ASSIGN_TYPE_TRANSACTIONS,
    #    _('All users making relevant transactions')),
)

AUTO_QTY_TYPE_TERMINALS = "NUM_TERMINALS"
AUTO_QTY_TYPE_TERMINALS_MINUS_ONE = "NUM_TERMINALS-1"
AUTO_QTY_TYPE_SIM_CARDS = "NUM_SIM_CARDS"
AUTO_QTY_TYPE_TRANSACTION_VALUE = "TRANSACTION_VALUE"
AUTO_QTY_TYPE_TRANSACTION_POINTS = "TRANSACTION_POINTS"
AUTO_QTY_TYPE_TRANSACTION_COUNT = "TRANSACTION_COUNT"
AUTO_QTY_TYPES = (
    (AUTO_QTY_TYPE_TERMINALS,
     _('Number of terminals assigned')),
    (AUTO_QTY_TYPE_TERMINALS_MINUS_ONE,
     _('Number of extra terminals assigned (first is free)')),
    (AUTO_QTY_TYPE_SIM_CARDS,
     _('Number of SIM cards assigned')),
    (AUTO_QTY_TYPE_TRANSACTION_COUNT,
     _('Number of transactions')),
    (AUTO_QTY_TYPE_TRANSACTION_VALUE,
     _('Value of transactions (euros)')),
    (AUTO_QTY_TYPE_TRANSACTION_POINTS,
     _('Value of transactions (points)')),
)

FILE_TYPE_TF_PRODUCTS = 'products'
FILE_TYPE_TF_USERS = 'users'
FILE_TYPE_TF_INVOICES = 'invoices'
FILE_TYPE_TF_EXTRA_CSV = 'extra_csv'   # not currently used
FILE_TYPES = (
    (FILE_TYPE_TF_PRODUCTS, FILE_TYPE_TF_PRODUCTS),
    (FILE_TYPE_TF_USERS, FILE_TYPE_TF_USERS),
    (FILE_TYPE_TF_INVOICES, FILE_TYPE_TF_INVOICES),
    (FILE_TYPE_TF_EXTRA_CSV, FILE_TYPE_TF_EXTRA_CSV),
)

# Might want this in settings, or even BillingSettings,
# but let's just get this working for now
MONTHLY_EXTRA_TWINFIELD_FILES = [
    'EXPORT_INVOICES',
]

def load_dynamic_settings():
    from .models import BillingSettings
    return BillingSettings.load()
