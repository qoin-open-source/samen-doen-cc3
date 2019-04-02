# encoding: utf-8
""" Invoice module utilities. """
import codecs
import datetime
import logging
import importlib

from decimal import Decimal
from io import BytesIO

from django.conf import settings

# from constance import config

from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.tables import Table, TableStyle
import xlwt

from .models import Invoice, InvoiceLine, PaymentStatus
from .pdf import draw_pdf

logger = logging.getLogger(__name__)


def auto_create_invoice(cc3_profile, currency, sender, amount=None,
                        invoice_type='monthly', invoice_description=''):
    """ Auto-create an invoice for this user.

    If the amount isn't specified, use Django settings
    to and AUTO_INVOICE_AMOUNT and determine the amount for this invoice.

    Returns if the invoice could be created successfully.
    """
    today = datetime.date.today()

    nr_days_due = getattr(settings, 'AUTO_INVOICE_DUE_DATE_DAYS', None)
    if not nr_days_due:
        logger.error(u"""Unable to create automatic invoice,
                     AUTO_INVOICE_DUE_DATE_DAYS has not been defined in your
                     settings.py""")
        return False

    if not amount:
        auto_invoice_amount = getattr(settings, 'AUTO_INVOICE_AMOUNT', None)
        if not nr_days_due or not auto_invoice_amount:
            logger.error(u"""Unable to create automatic invoice,
                         AUTO_INVOICE_AMOUNT has not been defined
                         in your settings.py""")
            return False
        try:
            amount = Decimal(auto_invoice_amount)
        except:  # Messy way to call a function specified in settings
            amount = eval(auto_invoice_amount + '(cc3_profile)')

    to_be_paid_status = PaymentStatus.objects.filter(
        is_active=True, is_paid=False
    )
    if not to_be_paid_status:
        logger.error(u"""Payment status with 'is_active' True and 'is_paid'
            False is not defined""")
        return False
    to_be_paid_status = to_be_paid_status[0]

    if Invoice.objects.filter(to_user=cc3_profile.user,
                              inv_date__month=today.month,
                              inv_date__year=today.year,
                              automatic_invoice=True):
        logger.info(u"""User already has received an automatic invoice
            this month, not creating a new invoice""")
        return False

    invoice = Invoice(
        from_user=sender, to_user=cc3_profile.user, inv_date=today,
        due_date=today+datetime.timedelta(days=nr_days_due),
        currency=currency, payment_status=to_be_paid_status,
        automatic_invoice=True,
        admin_comment=u"Automatic invoice of type {0}".format(invoice_type)
    )
    invoice.save()

    line = InvoiceLine(
        invoice=invoice, description=invoice_description,
        quantity=1, amount=amount)
    line.save()

    return True


def get_total_outstanding(user):
    """ Return the total amount of money the user owes via Invoices. """
    invoices = Invoice.objects.filter(
        to_user=user, payment_status__is_paid=False)
    total = Decimal()
    for invoice in invoices:
        total += invoice.get_total()
    return total


def generate_invoice_excel(invoice):
    """ Generate Excel Invoice. """
    raise NotImplementedError


def generate_invoice_pdf(invoice):
    """ Generate Invoice PDF. """
    output = BytesIO()
    draw_pdf_module = getattr(settings, 'INVOICE_DRAW_PDF_MODULE', None)
    if not draw_pdf_module:
        draw_pdf(output, invoice)
    else:
        draw_pdf_module = importlib.import_module(draw_pdf_module)
        draw_pdf_module.draw_pdf(output, invoice)
    pdf = output.getvalue()
    return pdf
