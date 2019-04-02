from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _


class AccountsApphook(CMSApp):
    name = _("Accounts")
    urls = ["cc3.accounts.urls"]
    app_name = 'accounts_ns'

apphook_pool.register(AccountsApphook)
