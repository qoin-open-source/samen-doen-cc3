from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _


UPLOAD_UID_EMAIL = 'EMAIL'
UPLOAD_UID_CARD = 'CARD'
UPLOAD_UID_OWN_ID = 'OWN'
UPLOAD_UID_USER_ID = 'USERID'

UPLOAD_CSV_DELIMITERS = ",;"   # only these delimiters permitted here

def get_bulk_upload_uid_choices():
    site = Site.objects.get_current()
    return (
        (UPLOAD_UID_EMAIL, _(u"Email address")),
        (UPLOAD_UID_CARD, _(u"Card number")),
        #(UPLOAD_UID_OWN_ID, _(u"Your own id number")),
        # not doing this for now -- needs to be generalised
        (UPLOAD_UID_USER_ID, _(u"{0} user id").format(site.name)),
    )