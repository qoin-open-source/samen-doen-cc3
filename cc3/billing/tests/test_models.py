from datetime import timedelta, date
import logging

from django.test import TestCase

from cc3.cards.models import Terminal
from cc3.cards.tests.test_factories import TerminalFactory
from cc3.cyclos.tests.test_factories import (
    CC3ProfileFactory, CyclosGroupFactory,
    )

from .test_factories import (
    ProductFactory, ProductPricingFactory, AssignedProductFactory,
    InvoiceFactory
    )
from ..common import (BILLING_PERIOD_ONEOFF,
    AUTO_QTY_TYPE_TERMINALS, AUTO_QTY_TYPE_TERMINALS_MINUS_ONE,
    AUTO_ASSIGN_TYPE_TERMINAL_RENTAL
    )
from ..models import (
    TaxRegime,
    # Product, ProductPricing, Invoice, InvoiceItem,
    AssignedProduct, TerminalDeposit,
    apply_tax, get_discount, get_percent,
    )


LOG = logging.getLogger(__name__)


class UtilsTestCase(TestCase):

    def test_apply_tax(self):
        result = apply_tax(100, 20)
        self.assertEqual(result, 120)

    def test_apply_tax_zero_tax(self):
        result = apply_tax(99, 0)
        self.assertEqual(result, 99)

    def test_apply_tax_decimal(self):
        result = apply_tax(100, 12.5)
        self.assertEqual(result, 112.5)

    def test_get_percent(self):
        result = get_percent(100, 20)
        self.assertEqual(result, 20)

    def test_get_percent_zero_percent(self):
        result = get_percent(99, 0)
        self.assertEqual(result, 0)

    def test_get_percent_decimal(self):
        result = get_percent(100, 12.5)
        self.assertEqual(result, 12.5)

    def test_get_discount(self):
        result = get_discount(100, 20)
        self.assertEqual(result, -20)

    def test_get_discount_zero_percent(self):
        result = get_discount(99, 0)
        self.assertEqual(result, 0)

    def test_get_discount_decimal(self):
        result = get_discount(100, 12.5)
        self.assertEqual(result, -12.5)


class ProductTestCase(TestCase):

    def setUp(self):
        self.cyclos_group = CyclosGroupFactory.create()
        self.cc3_profile = CC3ProfileFactory.create(
            cyclos_group=self.cyclos_group)

        self.today = date.today()
        self.tomorrow = date.today() + timedelta(days=1)

    def test_create(self):
        product = ProductFactory.create()
        self.assertEqual(product.billing_frequency, BILLING_PERIOD_ONEOFF)

    def test_is_discountable(self):
        product = ProductFactory.create(max_discount_percent=20)
        self.assertTrue(product.is_discountable)

    def test_is_not_discountable(self):
        product = ProductFactory.create(max_discount_percent=0)
        self.assertFalse(product.is_discountable)

    def test_valid_for_user(self):
        product = ProductFactory.create()
        product.user_groups.add(self.cc3_profile.cyclos_group)
        self.assertTrue(product.is_valid_for_user(self.cc3_profile))

    def test_not_valid_for_user(self):
        product = ProductFactory.create()
        self.assertFalse(product.is_valid_for_user(self.cc3_profile))

    def test_get_pricing_for_date(self):
        tax_regime = TaxRegime.objects.create(name="VAT", percent=21)
        product = ProductFactory.create(
            tax_regime=tax_regime,
            max_discount_percent=25)
        pricing1 = ProductPricingFactory.create(
            product=product, valid_from=self.today, unit_price_euros=10)
        pricing = product.get_pricing_for_date(price_date=self.today)
        self.assertEqual(pricing, pricing1)

    def test_no_valid_price_info(self):
        tax_regime = TaxRegime.objects.create(name="VAT", percent=21)
        product = ProductFactory.create(
            tax_regime=tax_regime,
            max_discount_percent=25)
        ProductPricingFactory.create(
            product=product, valid_from=self.tomorrow, unit_price_euros=10)
        pricing = product.get_pricing_for_date(price_date=self.today)
        self.assertEqual(pricing, None)


class AssignedProductTestCase(TestCase):

    def setUp(self):
        self.today = date.today()
        self.tomorrow = date.today() + timedelta(days=1)

        self.cyclos_group = CyclosGroupFactory.create()
        self.cc3_profile = CC3ProfileFactory.create(
            cyclos_group=self.cyclos_group)
        self.tax_regime = TaxRegime.objects.create(name="Big tax", percent=50)
        self.product = ProductFactory.create(
            tax_regime=self.tax_regime,
            max_discount_percent=25)
        self.terminal_qty_product = ProductFactory.create(
            auto_qty_type=AUTO_QTY_TYPE_TERMINALS)
        self.terminal_qty_product.user_groups.add(self.cyclos_group)
        self.terminal_qty_minus_one_product = ProductFactory.create(
            auto_qty_type=AUTO_QTY_TYPE_TERMINALS_MINUS_ONE)
        self.terminal_qty_minus_one_product.user_groups.add(self.cyclos_group)
        self.terminal_rental_product = ProductFactory.create(
            auto_assign_type=AUTO_ASSIGN_TYPE_TERMINAL_RENTAL,
            auto_qty_type=AUTO_QTY_TYPE_TERMINALS)
        self.terminal_rental_product.user_groups.add(self.cyclos_group)

    def test_create(self):
        AssignedProduct.objects.create(
            product=self.product,
            user_profile=self.cc3_profile,
            start_date=self.today,
            quantity=1,
        )
        self.assertEqual(self.cc3_profile.assigned_products.count(), 1)

    def test_get_prices_for_date(self):
        ProductPricingFactory.create(
            product=self.product, valid_from=self.today, unit_price_euros=10)
        ap = AssignedProduct.objects.create(
            product=self.product,
            user_profile=self.cc3_profile,
            start_date=self.today,
            quantity=2,
            discount_percent=20,
        )
        price = ap.get_prices_for_date(price_date=self.today)
        self.assertEqual(price['unit_price_ex_tax'], 10)
        self.assertEqual(price['unit_price_incl_tax'], 15)
        self.assertEqual(price['total_price_ex_tax'], 20)
        self.assertEqual(price['total_price_incl_tax'], 30)
        self.assertEqual(price['discount_amount_ex_tax'], -4)
        self.assertEqual(price['discount_amount_incl_tax'], -6)

    def test_no_valid_prices_for_date(self):
        ProductPricingFactory.create(
            product=self.product, valid_from=self.tomorrow,
            unit_price_euros=10)
        ap = AssignedProduct.objects.create(
            product=self.product,
            user_profile=self.cc3_profile,
            start_date=self.today,
            quantity=2,
            discount_percent=20,
        )
        price = ap.get_prices_for_date(price_date=self.today)
        self.assertEqual(price, {})

# TODO: more gt_prices_for_date tests, with different billing types etc.

    def test_generate_next_invoice_item(self):
        ProductPricingFactory.create(
            product=self.product, valid_from=self.today, unit_price_euros=10)
        ap = AssignedProduct.objects.create(
            product=self.product,
            user_profile=self.cc3_profile,
            start_date=self.today,
            quantity=2,
            discount_percent=20,
        )
        invoice = InvoiceFactory.create(
            invoice_date=self.today,
            user_profile=self.cc3_profile,
            invoicing_company=self.product.invoiced_by,
        )
        ii = ap.generate_next_invoice_item(invoice)
        self.assertEqual(ii.unit_price_ex_tax, 10)
        self.assertEqual(ii.unit_price_incl_tax, 15)
        self.assertEqual(ii.discount_amount_ex_tax, -4)
        self.assertEqual(ii.discount_amount_incl_tax, -6)

    def test_update_auto_qty_terminals(self):
        ap = AssignedProduct.objects.create(
            product=self.terminal_qty_product,
            user_profile=self.cc3_profile,
            start_date=self.today,
            quantity=10,
        )
        term1 = TerminalFactory(business=self.cc3_profile.user)
        term2 = TerminalFactory(business=self.cc3_profile.user)
        ap.update_auto_quantity()
        self.assertEqual(2, ap.quantity)

    def test_update_auto_qty_terminals_minus_one(self):
        ap = AssignedProduct.objects.create(
            product=self.terminal_qty_minus_one_product,
            user_profile=self.cc3_profile,
            start_date=self.today,
            quantity=10,
        )
        term1 = TerminalFactory(business=self.cc3_profile.user)
        term2 = TerminalFactory(business=self.cc3_profile.user)
        ap.update_auto_quantity()
        self.assertEqual(1, ap.quantity)

    def test_update_auto_qty_terminals_never_negative(self):
        ap = AssignedProduct.objects.create(
            product=self.terminal_qty_minus_one_product,
            user_profile=self.cc3_profile,
            start_date=self.today,
            quantity=10,
        )
        ap.update_auto_quantity()
        self.assertEqual(0, ap.quantity)

    def test_auto_assign_terminal_product(self):
        """Tests terminal rental product assignment is auto-created where necessary"""
        # should auto-create an AP
        term1 = TerminalFactory(business=self.cc3_profile.user)
        self.assertEqual(1, self.cc3_profile.assigned_products.filter(
            product=self.terminal_rental_product).count())

    def test_auto_assign_terminal_product_reassignment(self):
        """Tests terminal rental product assignment is auto-updated when Terminal reassigned"""
        # should auto-create an AP
        term1 = TerminalFactory(business=self.cc3_profile.user)
        # should create an AP with qty 1
        self.assertEqual(1, self.cc3_profile.assigned_products.get(
            product=self.terminal_rental_product).quantity)
        term2 = TerminalFactory(business=self.cc3_profile.user)
        # should update qty to 2 -- re-get the AP to see if it has
        self.assertEqual(2, self.cc3_profile.assigned_products.get(
            product=self.terminal_rental_product).quantity)

        # now reassign one of the Terminals to someone else
        new_profile = CC3ProfileFactory.create(
            cyclos_group=self.cyclos_group)
        self.assertEqual(0, new_profile.assigned_products.filter(
            product=self.terminal_rental_product).count())

        term1.business=(new_profile.user)
        term1.save()

        # should both have APs, each with quantity 1
        self.assertEqual(1, self.cc3_profile.assigned_products.get(
            product=self.terminal_rental_product).quantity)
        self.assertEqual(1, new_profile.assigned_products.get(
            product=self.terminal_rental_product).quantity)

    def test_overlapping_dates_distinct_closed_periods(self):
        """Tests overlapping dates check for non-overlapping periods"""
        ap1 = AssignedProductFactory(
            product=self.product, user_profile=self.cc3_profile,
            quantity=1,
            end_date=self.today + timedelta(days=10))
        ap2 = AssignedProductFactory(
            product=ap1.product,user_profile=ap1.user_profile,
            quantity=1,
            start_date = self.today + timedelta(days=20))
        self.assertFalse(ap1.dates_overlap_with(ap2))

    def test_overlapping_dates_overlapping_closed_periods(self):
        """Tests overlapping dates check for overlapping periods"""
        ap1 = AssignedProductFactory(
            product=self.product, user_profile=self.cc3_profile,
            quantity=1,
            end_date=self.today + timedelta(days=10))
        ap2 = AssignedProductFactory(
            product=ap1.product,user_profile=ap1.user_profile,
            quantity=1,
            start_date = self.today + timedelta(days=10))
        self.assertTrue(ap1.dates_overlap_with(ap2))

    # TODO: more dates_overlap_with tests
    # TODO: max and min qty tests


class TerminalDepositTestCase(TestCase):

    def setUp(self):
        self.cyclos_group = CyclosGroupFactory.create()
        self.cc3_profile1 = CC3ProfileFactory.create(
            cyclos_group=self.cyclos_group)
        self.cc3_profile2 = CC3ProfileFactory.create(
            cyclos_group=self.cyclos_group)
        self.user1 = self.cc3_profile1.user
        self.user2 = self.cc3_profile2.user
        #self.term1 = TerminalFactory()

    def test_assign_new_terminal_to_business(self):
        """Test deposit is due if terminal assigned to business"""
        term = TerminalFactory(business=self.user1)
        td = TerminalDeposit.objects.get(business=self.user1, terminal=term)
        self.assertTrue(td.deposit_due)

    def test_reassign_terminal(self):
        """Test desposit and refund handled correctly for reassigned terminal"""
        term = TerminalFactory(business=self.user1)
        # pretend this is  long-term assignment, so deposit is no longer due
        td1 = TerminalDeposit.objects.get(business=self.user1, terminal=term)
        td1.record_deposit_charged()
        term.business=self.user2
        term.save()
        # get it again, because it's been changed behind our back...
        td1 = TerminalDeposit.objects.get(business=self.user1, terminal=term)
        self.assertTrue(td1.refund_due)
        td2 = TerminalDeposit.objects.get(business=self.user2, terminal=term)
        self.assertTrue(td2.deposit_due)

    def test_unassign_terminal(self):
        """Test refund if terminal unassigned"""
        term = TerminalFactory(business=self.user1)
        # pretend this is  long-term assignment, so deposit is no longer due
        td1 = TerminalDeposit.objects.get(business=self.user1, terminal=term)
        td1.record_deposit_charged()
        term.business=None
        term.save()
        td1 = TerminalDeposit.objects.get(business=self.user1, terminal=term)
        self.assertTrue(td1.refund_due)


    def test_no_refund_if_deposit_still_due(self):
        """Test no refund if deposit still due when terminal unassigned"""
        term = TerminalFactory(business=self.user1)
        term.business=self.user2
        term.save()
        td1 = TerminalDeposit.objects.get(business=self.user1, terminal=term)
        self.assertFalse(td1.refund_due)
        self.assertFalse(td1.deposit_due)

    def test_terminal_not_assigned_to_business(self):
        """Test no deposit is due if terminal not assigned to business"""
        term = TerminalFactory(business=None)
        tds = TerminalDeposit.objects.filter(terminal=term)
        self.assertEqual(tds.count(), 0)

    def test_assign_existing_terminal_to_business(self):
        """Test deposit is due if unassigned terminal assigned to business"""
        term = TerminalFactory(business=None)
        term.business = self.user1
        term.save()
        td = TerminalDeposit.objects.get(business=self.user1, terminal=term)
        self.assertTrue(td.deposit_due)
