from django.utils.translation import ugettext_lazy as _

### Ad payment types ###

AD_PAYMENT_REGULAR = 'regular'
AD_PAYMENT_EURO = 'euro'

AD_PAYMENT_CHOICES = (
    (AD_PAYMENT_REGULAR, _('Regular')),
    (AD_PAYMENT_EURO, _('Euro')),
)

### Ad status variables ###

AD_STATUS_ACTIVE = 'active'
AD_STATUS_DISABLED = 'disabled'
AD_STATUS_ONHOLD = 'onhold'

AD_DISABLE_CHOICES = (
    (AD_STATUS_ACTIVE, _('Enabled')),
    (AD_STATUS_DISABLED, _('Disabled')),
)

AD_STATUS_CHOICES = (
    (AD_STATUS_ACTIVE, _('Enabled')),
    (AD_STATUS_DISABLED, _('Disabled')),
    (AD_STATUS_ONHOLD, _('On hold')),
)
