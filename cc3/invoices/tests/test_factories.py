# -*- coding: utf-8 -*-

import logging
import datetime
import factory

from cc3.cyclos.tests.test_factories import UserFactory

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class PaymentStatusFactory(factory.DjangoModelFactory):
    description = factory.Sequence(lambda n: 'Payment Status {0}'.format(n))
    is_active = True
    is_paid = False

    class Meta:
        model = 'invoices.PaymentStatus'


class CurrencyFactory(factory.DjangoModelFactory):
    # Primary key, so this needs to be unique
    code = factory.Sequence(lambda n: 'Q{0}'.format(n))
    name = 'Euro'
    symbol = '€'

    class Meta:
        model = 'invoices.Currency'


class InvoiceFactory(factory.DjangoModelFactory):
    number = factory.Sequence(lambda n: n)
    from_user = factory.SubFactory(UserFactory)
    to_user = factory.SubFactory(UserFactory)
    currency = factory.SubFactory(CurrencyFactory)
    payment_status = factory.SubFactory(PaymentStatusFactory)
    inv_date = datetime.date.today()
    due_date = datetime.date.today() + datetime.timedelta(days=14)

    class Meta:
        model = 'invoices.Invoice'
