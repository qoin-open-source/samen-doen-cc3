from calendar import monthrange
from datetime import date, datetime
import logging

from django.db import transaction, IntegrityError
from django.utils.translation import ugettext, ugettext_lazy as _

#from cc3.cyclos import backends

from .models import (
    AssignedProduct, Invoice, InvoiceSet, TerminalDeposit, Product)
from .common import (
    AUTO_ASSIGN_TYPE_TERMINAL_DEPOSIT, AUTO_ASSIGN_TYPE_TERMINAL_REFUND,
    AUTO_ASSIGN_TYPE_TERMINAL_RENTAL, AUTO_ASSIGN_TYPE_SIM_CARD,
    AUTO_ASSIGN_TYPE_USER_GROUPS,
    AUTO_QTY_TYPE_TERMINALS, AUTO_QTY_TYPE_TERMINALS_MINUS_ONE,
    AUTO_QTY_TYPE_SIM_CARDS, AUTO_QTY_TYPE_TRANSACTION_VALUE,
    AUTO_QTY_TYPE_TRANSACTION_COUNT, AUTO_QTY_TYPE_TRANSACTION_POINTS,
    MONTHLY_EXTRA_TWINFIELD_FILES)


LOG = logging.getLogger(__name__)


def _pre_monthly_invoicing_actions(period_start, period_end):
    """Perform auto-updates needed before generating invoices

    i.e.
    - create one-off AssignedProducts for terminal deposits and refunds
    - update quantities for transaction products
    """
    try:
        terminal_deposit_product = Product.objects.get(
            auto_assign_type=AUTO_ASSIGN_TYPE_TERMINAL_DEPOSIT)

        terminal_deposits = TerminalDeposit.objects.filter(deposit_due=True)
        for td in terminal_deposits.all():
            # create or update an assigned product for this month
            ap, created = AssignedProduct.objects.get_or_create(
                product=terminal_deposit_product,
                user_profile=td.business.cc3_profile,
                start_date=period_start,
                end_date=period_end,
                next_invoice_date=period_end,
                defaults={'quantity': 1},
                )
            if not created:
                ap.quantity += 1
                ap.save()

            td.record_deposit_charged(period_end)

    except Product.DoesNotExist:
        LOG.error("Terminal deposit product not found -- no deposits charged")

    try:
        terminal_refund_product = Product.objects.get(
            auto_assign_type=AUTO_ASSIGN_TYPE_TERMINAL_REFUND)

        terminal_refunds = TerminalDeposit.objects.filter(refund_due=True)
        for td in terminal_refunds.all():
            # create or update an assigned product for this month
            ap, created = AssignedProduct.objects.get_or_create(
                product=terminal_refund_product,
                user_profile=td.business.cc3_profile,
                start_date=period_start,
                end_date=period_end,
                next_invoice_date=period_end,
                defaults={'quantity': 1},
                )
            if not created:
                ap.quantity += 1
                ap.save()

            td.record_deposit_refunded(period_end)

    except Product.DoesNotExist:
        LOG.error("Terminal refund product not found -- no deposits refunded")

    # auto-assign products for user groups
    for product in Product.objects.filter(
            auto_assign_type=AUTO_ASSIGN_TYPE_USER_GROUPS).all():
        product.assign_to_user_groups()

    for txn_ap in AssignedProduct.objects.filter(
            product__auto_qty_type__in=[AUTO_QTY_TYPE_TRANSACTION_VALUE,
                                        AUTO_QTY_TYPE_TRANSACTION_POINTS,
                                        AUTO_QTY_TYPE_TRANSACTION_COUNT],
            next_invoice_date__gte=period_start,
            next_invoice_date__lte=period_end):
        txn_ap.update_auto_quantity(period_start, period_end, save=True)


def generate_monthly_invoices(year, month, invoice_date=None,
                              send_to_twinfield=True):
    """Generate an Invoice and InvoiceItems for the given month"""

    LOG.info("Monthly invoice run for {0:02d}-{1}".format(month, year))

    # monthly invoicing done as an atomic transaction, rolling back if
    # anything goes wrong
    try:
        with transaction.atomic():
            if not invoice_date:
                invoice_date = date.today()

            numdays = monthrange(year, month)[1]
            period_start = date(year, month, 1)
            period_end = date(year, month, numdays)

            description = '{0:02d}-{1}'.format(month, year)

            invoice_set = InvoiceSet.objects.create(
                description=description,
                period_start=period_start, period_end=period_end)
            audit_messages = [description, '',]

            # perform pre-invoicing updates and actions
            msg = ugettext(".. Performing pre-invoicing actions")
            LOG.info(msg)
            audit_messages.append(msg)
            _pre_monthly_invoicing_actions(period_start, period_end)
            audit_messages.append(
                ugettext(".. Completed pre-invoicing actions"))

            for assigned_product in AssignedProduct.objects.filter(
                next_invoice_date__gte=period_start,
                next_invoice_date__lte=period_end):

                msg = _("{0}, next payment date {1}...").format(
                    assigned_product, assigned_product.next_invoice_date)
                audit_messages.append(msg)

                invoice, _created = Invoice.objects.get_or_create(
                    invoice_set=invoice_set,
                    invoicing_company=assigned_product.product.invoiced_by,
                    invoice_date=invoice_date,
                    user_profile=assigned_product.user_profile,
                    description=description,
                    date_exported=None,
                )

                # generate the invoice item
                invoice_item = assigned_product.generate_next_invoice_item(
                    invoice)
                if not invoice_item:
                    audit_messages.append(
                        ugettext("...Failed (missing price?)"))
    except Exception:
        LOG.error("\n!! Monthly invoicing failed. Database has "
                  "been rolled back so it can be safely re-tried once the "
                  "problem has been fixed")
        raise

    for invoice in invoice_set.invoices.all():
        if not invoice.items.count():
            invoice.delete()
    num_invoices = invoice_set.invoices.count()
    LOG.info(".. Generated {0} invoices".format(num_invoices))
    invoice_set.description = _(
        'Monthly invoice run for {0:02d}-{1} ({2} invoices)'
        ).format(month, year, num_invoices)
    audit_messages.extend(('', invoice_set.description))
    invoice_set.invoices_created_at = datetime.now()
    invoice_set.save()

    if invoice_set.invoices.count():
        invoice_set.generate_twinfield_files()
        LOG.info(".. Generated Twinfield files")
    #invoice_set.generate_extra_twinfield_files(
    #    MONTHLY_EXTRA_TWINFIELD_FILES)
    #if invoice_set.extras_generated_at:
    #    LOG.info(".. Generated Extra Twinfield files")
    #else:
    #    LOG.error(".. Failed to generate Extra Twinfield files")
    if send_to_twinfield:
        #if invoice_set.extras_generated_at and invoice_set.generated_at:
        if invoice_set.generated_at:
            invoice_set.send_twinfield_files()
            LOG.info(".. Sent files to Twinfield")
        else:
            LOG.error(".. Files not sent to Twinfield")


def generate_adhoc_invoices(assigned_products_qs,
                            invoice_date,
                            send_to_twinfield):
    "Generate an ad-hoc Invoice and InvoiceItems for queryset"""

    description = _('Ad-hoc invoice generated on {0}').format(
        datetime.now())

    num_items = 0
    error_messages = []

    invoice_set = InvoiceSet.objects.create(description=description)

    for assigned_product in assigned_products_qs.all():

        if not assigned_product.next_invoice_date:
            msg = _("'{0}' has no payment due "
                  "(next payment date is blank)").format(assigned_product)
            error_messages.append(msg)
            continue

        product = assigned_product.product
        if not product.can_invoice_adhoc:
            msg = _("'{1}' product cannot be invoiced ad hoc").format(
                    product.get_billing_frequency_display(), assigned_product)
            error_messages.append(msg)
            continue
        invoice, created = Invoice.objects.get_or_create(
            invoice_set=invoice_set,
            invoicing_company=product.invoiced_by,
            invoice_date=invoice_date,
            user_profile=assigned_product.user_profile,
            description=description,
            date_exported=None,
        )

        # generate the invoice item
        assigned_product.generate_next_invoice_item(invoice)
        num_items += 1

    num_invoices = invoice_set.invoices.count()
    if num_invoices:
        invoice_set.invoices_created_at = datetime.now()
        invoice_set.description = _(
            '{0} ad-hoc invoice(s) generated on {1}').format(
            num_invoices, invoice_set.invoices_created_at)
        invoice_set.save()   # it's saved again in the following, but done
                             # here so we know the invoices were created OK

        invoice_set.generate_twinfield_files()
        if send_to_twinfield:
            invoice_set.send_twinfield_files()

    else:
        # For ad-hoc invoicing (as opposed to the monthly run) we don't need
        # to keep an empty InvoiceSet because any errors will have been
        # shown on the webpage
        invoice_set.delete()

    return num_invoices, num_items, error_messages


def terminal_rental_product_for_group(cyclos_group):
    products = Product.objects.filter(
        auto_assign_type=AUTO_ASSIGN_TYPE_TERMINAL_RENTAL).filter(
        user_groups=cyclos_group)

    if not products.count():
        LOG.warning(
            "No terminal rental product for group {0}".format(cyclos_group))
        return None

    if products.count() > 1:
        LOG.warning("More than one terminal rental product for group {0}. "
                    "Using {1}".format(cyclos_group, products[0]))
    return products[0]


def sim_card_product_for_group(cyclos_group):
    products = Product.objects.filter(
        auto_assign_type=AUTO_ASSIGN_TYPE_SIM_CARD).filter(
        user_groups=cyclos_group)

    if not products.count():
        LOG.warning(
            "No SIM card product for group {0}".format(cyclos_group))
        return None

    if products.count() > 1:
        LOG.warning("More than one SIM card product for group {0}. "
                    "Using {1}".format(cyclos_group, products[0]))
    return products[0]


def update_terminal_products(user):
    """Make sure user's SIM card and terminal-rental products are up to date

    i.e. update the quantity on any products with auto-update type
    AUTO_QTY_TYPE_SIM_CARDS, AUTO_QTY_TYPE_TERMINALS or
    AUTO_QTY_TYPE_TERMINALS_MINUS_ONE.
    If the quantity is zero, deletes the AP

    Creates a new AssignedProduct if necessary
    """
    try:
        cc3_profile = user.cc3_profile
    except AttributeError:
        return
    today = date.today()
    terminal_products = user.cc3_profile.assigned_products.filter(
        product__auto_assign_type=AUTO_ASSIGN_TYPE_TERMINAL_RENTAL).exclude(
        start_date__gt=today).exclude(end_date__lt=today)

    if terminal_products.count():
        # update the quantity in each, and delete if it's zero
        for ap in terminal_products.all():
            ap.update_auto_quantity(save=False)
            if ap.quantity > 0:
                ap.save()
            else:
                ap.delete()

    else:
        # create a new AssignedProduct if quantity is nonzero
        product = terminal_rental_product_for_group(
            user.cc3_profile.cyclos_group)
        if product:
            ap = AssignedProduct(product=product,
                                 user_profile=user.cc3_profile)
            ap.update_auto_quantity(save=False)
            if ap.quantity > 0:
                ap.save()
        else:
            LOG.error("Failed to assign terminal rental product "
                      "for user {0}".format(user))

    sim_card_products = user.cc3_profile.assigned_products.filter(
        product__auto_assign_type=AUTO_ASSIGN_TYPE_SIM_CARD).exclude(
        start_date__gt=today).exclude(end_date__lt=today)

    if sim_card_products.count():
        # update the quantity in each, and delete if it's zero
        for ap in sim_card_products.all():
            ap.update_auto_quantity(save=False)
            if ap.quantity > 0:
                ap.save()
            else:
                ap.delete()

    else:
        # create a new AssignedProduct if quantity is nonzero
        product = sim_card_product_for_group(
            user.cc3_profile.cyclos_group)
        if product:
            ap = AssignedProduct(product=product,
                                 user_profile=user.cc3_profile)
            ap.update_auto_quantity(save=False)
            if ap.quantity > 0:
                ap.save()
        else:
            LOG.error("Failed to assign SIM card product "
                      "for user {0}".format(user))
