"""
MONTHLY_EXTRA_TWINFIELD_SQL dict of SQL snippets.
(See the equivalent file in statistics app if it becomes necessary to
override these on a per-project basis)
"""

from export_invoices import export_invoices_sql

# format for strftime suitable as the argument to DATE() in SQL
SQL_DATE_FORMAT = "%Y-%m-%d"

MONTHLY_EXTRA_TWINFIELD_SQL = {
'EXPORT_INVOICES': export_invoices_sql,
}