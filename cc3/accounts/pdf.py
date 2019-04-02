# encoding: utf-8
"""
Transaction PDF drawing functions adapted from:
https://github.com/simonluijk/django-invoice/blob/master/invoice/pdf.py

BSD licensed.
"""
import os

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (Image, Table, Paragraph,
                                SimpleDocTemplate, Spacer)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib import utils
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet

from django.conf import settings
from django.utils.formats import localize, number_format, date_format
from django.utils.translation import ugettext as _

from cc3.cyclos.models import User

if settings.DEBUG:
    LOGO_IMG = os.path.join(
        settings.PROJECT_DIR, 'static/images/general/logo.png')
else:
    LOGO_IMG = os.path.join(settings.STATIC_ROOT, 'images/general/logo.png')


def get_image_width_height(path, width=4*cm):
    img = utils.ImageReader(path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    return width, width * aspect


class DrawTransactionsPDF(object):

    def __init__(self, output, user, transactions, month=None,
                 currency_symbol=settings.CURRENCY_SYMBOL,
                 current_balance=None):

        self.output = output
        self.user = user
        self.transactions = transactions
        self.currency_symbol = currency_symbol
        self.month = month
        self.current_balance = current_balance

        self.profile = user.cc3_profile

        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self.orange = (0.9, 0.5, 0.2)
        self.padding_x = 37

        # This controls the size of the gap for the header/static content.
        self.first_page_spacer = Spacer(1, 115)

    def coord(self, x, y, unit=1):
        """
        http://stackoverflow.com/questions/4726011/wrap-text-in-a-table-reportlab

        Helper class to help position flowables in Canvas objects.
        """
        x, y = x * unit, self.height - y * unit
        return x, y

    def render(self):
        self.doc = SimpleDocTemplate(self.output)
        self.story = [self.first_page_spacer]
        self.build_transactions_table()
        self.doc.build(self.story, onFirstPage=self.draw_header)

    def draw_header(self, canvas, doc):
        """ Draws the static (non-flowable content """
        self.c = canvas

        # Header
        h1 = self.styles['h1']
        h1.fontName = 'Helvetica'
        normal = self.styles['Normal']

        iwidth, iheight = get_image_width_height(LOGO_IMG)
        logo = Image(LOGO_IMG, width=iwidth, height=iheight)
        logo.wrapOn(self.c, self.height, self.width)
        logo_y = iheight + (1 * cm)
        logo.drawOn(self.c, *self.coord(self.padding_x, logo_y))

        # Address
        pro = self.profile
        address_data = [
            u"{} {}".format(pro.first_name, pro.last_name),
            pro.business_name,
            pro.address,
            pro.city,
            pro.postal_code,
        ]
        address_y = logo_y * 1.1 + normal.leading * len(address_data)
        address = Paragraph(u"<br/>".join(address_data), style=normal)
        address.wrapOn(self.c, self.height, self.width)
        address.drawOn(self.c, *self.coord(self.padding_x, address_y))

        # Account/transaction info
        # account_data = [_(u'Account number: %s') % pro.get_account_number()]
        account_data = []
        if self.month:
            account_data.append(_(u'Transactions for: %(date)s') %
                                {'date': date_format(self.month,
                                                     "YEAR_MONTH_FORMAT")})
        else:
            account_data.append(_(u'Last 10 transactions'))
            account_data.append(_(u'Current balance:') + u' {0} {1}'.format(
                                number_format(self.current_balance, 2),
                                self.currency_symbol))
        account_y = address_y * 1.2 + normal.leading * len(account_data)
        account = Paragraph(u"<br/>".join(account_data), style=normal)
        account.wrapOn(self.c, self.height, self.width)
        account.drawOn(self.c, *self.coord(self.padding_x, account_y))

    def build_transactions_table(self):
        """ Draws the transactions PDF """

        def get_transaction_user(transaction):
            if transaction.amount < 0:
                recipient = transaction.recipient
                if getattr(recipient, 'cc3_profile', False):
                    recipient = recipient.cc3_profile
                return _("Recipient:") + u" " + unicode(recipient)

            sender = transaction.sender
            if getattr(sender, 'cc3_profile', False):
                sender = sender.cc3_profile
            return _("Sender:") + u" " + unicode(sender)

        # Items
        data = [[_(u'Date'), _(u'From/To'), _(u'Description'), _(u'Amount')], ]
        for item in self.transactions:
            data.append([
                date_format(item.created.date()),
                Paragraph(get_transaction_user(item), self.styles['Normal']),
                Paragraph(item.description, self.styles['Normal']),
                u"{0}".format(number_format(item.amount, 2)),
            ])
        if not self.transactions:
            data.append([u'', _('No transactions in this month'), u''])

        table = Table(data,
                      colWidths=[2.5 * cm, 5 * cm, 8 * cm, 3 * cm, 3 * cm])
        table.setStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), (0.2, 0.2, 0.2)),
            ('GRID', (0, 0), (-1, -4), 1, (0.7, 0.7, 0.7)),
            ('GRID', (0, 0), (-1, -1), 1, (0.7, 0.7, 0.7)),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
        ])

        self.story.append(table)


def draw_transactions_pdf(
        output, user, transactions, currency_symbol=settings.CURRENCY_SYMBOL,
        month=None, current_balance=None):
    """
    Wrapper for DrawTransactionsPDF.
    """
    report = DrawTransactionsPDF(
        output, user, transactions, currency_symbol=currency_symbol,
        month=month, current_balance=current_balance)
    report.render()
