from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

class MarketplaceApphook(CMSApp):
    name = _("Marketplace")
    urls = ["cc3.marketplace.urls"]
    app_name = 'marketplace_ns'

apphook_pool.register(MarketplaceApphook)
