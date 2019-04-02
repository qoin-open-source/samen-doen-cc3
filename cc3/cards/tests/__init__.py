from .test_api import (
    CardDetailViewTestCase, CardPaymentTest, CardRegisterViewTestCase,
    OperatorLoginViewTestCase, TerminalLoginViewTestCase, CardRewardTest,
    NewAccountViewTestCase, CardPermittedDetailTest, UserLoginViewTestCase)
from .test_forms import CSVFileFormTestCase, OwnerRegisterCardFormTestCase
from .test_views import (
    NFCTerminalsListViewTestCase, OperatorsCreateViewTestCase,
    OperatorsDeleteViewTestCase, OperatorsUpdateViewTestCase,
    CardNumberAdminViewTestCase, OwnerManageCardViewTestCase)
