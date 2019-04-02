from django.utils.translation import ugettext_lazy as _

from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool


class CommunityAdminApphook(CMSApp):
    name = _('CommunityAdmin')
    urls = ['cc3.communityadmin.urls']
    app_name = 'communityadmin_ns'

apphook_pool.register(CommunityAdminApphook)
