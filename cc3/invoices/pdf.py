# encoding: utf-8
"""
Invoice PDF drawing functions adapted from:
https://github.com/simonluijk/django-invoice/blob/master/invoice/pdf.py

BSD licensed.
"""
import logging
import os

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table
from reportlab.lib import utils
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from django.conf import settings
from django.utils.translation import ugettext as _

logger = logging.getLogger(__name__)

logo_image = getattr(
    settings, 'LOGO_IMG',
    os.path.join(settings.PROJECT_DIR, 'static/img/logo.png'))


def get_image_width_height(path, width=4*cm):
    image = utils.ImageReader(path)
    image_width, image_height = image.getSize()
    aspect = image_height / float(image_width)

    return width, width * aspect


def draw_header(canvas):
    """ Draws the invoice header """
    try:
        width, height = get_image_width_height(logo_image)
        canvas.drawImage(logo_image, 1.0 * cm, -2.5 * cm, width, height)
    except IOError:
        # Logo image file does not exist.
        logger.error(u"The image logo file for generating PDFs doesn't exist.")


def draw_address(canvas):
    """ Draws the business address """
    business_details = (
        _(u'{0}').format(getattr(settings, 'CC3_SYSTEM_NAME', 'TradeQoin')),
        _(u'Street'),
        _(u'City'),
        _(u'Postal Code'),
    )
    canvas.setFont('Helvetica', 9)
    textobject = canvas.beginText(17 * cm, -2.5 * cm)
    for line in business_details:
        textobject.textLine(line)
    canvas.drawText(textobject)


def draw_footer(canvas, invoice):
    """ Draws the invoice footer """
    note = (
        _(u'Bank Details: Street address, Town, County, Postal Code'),
        _(u'Sort Code: 00-00-00 Account No: 00000000 (Quote invoice number).'),
        _(u'''Please pay via bank transfer or cheque.
        All payments should be made in {}.''').format(invoice.currency.code),
        _(u'Make cheques payable to {0}.').format(
            getattr(settings, 'CC3_SYSTEM_NAME', 'TradeQoin')),
    )
    textobject = canvas.beginText(1 * cm, -27 * cm)
    for line in note:
        textobject.textLine(line)
    canvas.drawText(textobject)


def draw_pdf(buffer, invoice):
    """ Draws the invoice """
    canvas = Canvas(buffer, pagesize=A4)
    canvas.translate(0, 29.7 * cm)
    canvas.setFont('Helvetica', 10)

    canvas.saveState()
    draw_header(canvas)
    canvas.restoreState()

    canvas.saveState()
    draw_footer(canvas, invoice)
    canvas.restoreState()

    canvas.saveState()
    draw_address(canvas)
    canvas.restoreState()

    currency_symbol = invoice.currency.symbol

    # Client address
    profile = invoice.to_user.cc3_profile
    textobject = canvas.beginText(1.5 * cm, -2.5 * cm)

    textobject.textLine(u"{} {}".format(profile.first_name, profile.last_name))
    textobject.textLine(profile.business_name)
    textobject.textLine(profile.address)
    textobject.textLine(profile.city)
    textobject.textLine(profile.postal_code)
    textobject.textLine(unicode(profile.country.name))
    canvas.drawText(textobject)

    # Info
    textobject = canvas.beginText(1.5 * cm, -6.75 * cm)
    textobject.textLine(_(u'Invoice no: {0}'.format(invoice.inv_no)))
    textobject.textLine(_(u'Invoice Date: {0}'.format(
        invoice.inv_date.strftime('%d %b %Y'))))
    canvas.drawText(textobject)

    # Items
    data = [
        [_(u'Qty'), _(u'Description'), _(u'Unit Price'), _(u'Tax'),
         _(u'Total')]
    ]

    for item in invoice.lines.all():
        data.append([
            item.quantity,
            item.description,
            u"{0:.2f} {1}".format(item.amount, currency_symbol),
            u"{0:.2f} {1}".format(item.get_tax(), currency_symbol),
            u"{0:.2f} {1}".format(item.grand_total, currency_symbol),
        ])

    data.append([u'', u'', u'', _(u'Sub total:'), u"{0:.2f} {1}".format(
        invoice.get_sub_total(), currency_symbol)])
    data.append([u'', u'', u'', _(u'Tax:'), u"{0:.2f} {1}".format(
        invoice.get_tax(), currency_symbol)])
    data.append([u'', u'', u'', _(u'Total:'), u"{0:.2f} {1}".format(
        invoice.get_total(), currency_symbol)])

    table = Table(data, colWidths=[1.5 * cm, 8.5 * cm, 3 * cm, 3 * cm, 3 * cm])
    table.setStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), (0.2, 0.2, 0.2)),
        ('GRID', (0, 0), (-1, -4), 1, (0.7, 0.7, 0.7)),
        ('GRID', (-2, -3), (-1, -1), 1, (0.7, 0.7, 0.7)),
        ('ALIGN', (-2, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
    ])
    table_widht, table_height, = table.wrapOn(canvas, 15 * cm, 19 * cm)
    table.drawOn(canvas, 1 * cm, -8 * cm - table_height)

    canvas.showPage()
    canvas.save()
