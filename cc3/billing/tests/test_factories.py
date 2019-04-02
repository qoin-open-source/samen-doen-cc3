import logging
import factory

from cc3.cyclos.tests.test_factories import CC3ProfileFactory

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class InvoicingCompanyFactory(factory.DjangoModelFactory):
    company_name = factory.Sequence(lambda n: 'InvoicingCompany {0}'.format(n))

    class Meta:
        model = 'billing.InvoicingCompany'


class TaxRegimeFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Tax Regime {0}'.format(n))

    class Meta:
        model = 'billing.TaxRegime'


class ProductFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Product {0}'.format(n))
    subarticle_code = factory.Sequence(lambda n: 'Subarticle Code {0}'.format(n))
    tax_regime = factory.SubFactory(TaxRegimeFactory)
    invoiced_by = factory.SubFactory(InvoicingCompanyFactory)

    class Meta:
        model = 'billing.Product'


class AssignedProductFactory(factory.DjangoModelFactory):
    product = factory.SubFactory(ProductFactory)
    user_profile = CC3ProfileFactory

    class Meta:
        model = 'billing.AssignedProduct'


class ProductPricingFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'billing.ProductPricing'


class InvoiceSetFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'billing.InvoiceSet'


class InvoiceFactory(factory.DjangoModelFactory):
    invoice_set = factory.SubFactory(InvoiceSetFactory)

    class Meta:
        model = 'billing.Invoice'