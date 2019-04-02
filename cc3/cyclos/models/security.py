from django.db import models
from django.utils.translation import ugettext_lazy as _

from adminsortable.models import Sortable
from easy_thumbnails.fields import ThumbnailerImageField

from ..utils import get_cyclos_channel_image_filename


class CyclosChannel(Sortable):
    """ Mirrors the channels in cyclos. """

    internal_name = models.CharField(
        max_length=50,
        help_text=_(u'Used to identify channel in Cyclos. Must be the same as '
                    u'the internal name in Cyclos'))
    display_name = models.CharField(
        max_length=100,
        help_text=_(u'Displayed to user on their security screen (can be the '
                    u'same as the display name in Cyclos)'))
    is_web_channel = models.BooleanField(
        default=False,
        help_text=_(u'Identify web channel, which is only disabled on the '
                    u'Django side'))
    image = ThumbnailerImageField(
        upload_to=get_cyclos_channel_image_filename, blank=True,
        height_field="height", width_field="width")

    class Meta:
        app_label = 'cyclos'
        verbose_name_plural = _(u'channels')
        ordering = ('order', 'display_name')

    def __unicode__(self):
        return self.display_name
