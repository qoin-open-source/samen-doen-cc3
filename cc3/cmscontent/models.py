from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _

import autoslug

from cms.models import PlaceholderField, CMSPlugin
from cms.plugin_base import CMSPluginBase

VALID_IDENTIFIER_CHOICES = (
    (
        'accounts_add_funds',
        'accounts_add_funds'
    ),
    (
        'accounts_credit_eligibility_criterea',
        'accounts_credit_eligibility_criterea'
    ),
    (
        'accounts_credit_application_procedure',
        'accounts_credit_application_procedure'
    ),
    (
        'accounts_credit_review',
        'accounts_credit_review'
    ),
    (
        'accounts_credit_further_questions',
        'accounts_credit_further_questions'
    ),
    (
        'accounts_apply_for_upgrade',
        'accounts_apply_for_upgrade'
    ),
    (
        'accounts_apply_for_upgrade_below_form',
        'accounts_apply_for_upgrade_below_form'
    ),
    (
        'registration_password_reset',
        'registration_password_reset'
    ),
    (
        'registration_login_message',
        'registration_login_message'
    ),
    (
        'accounts_exchange_to_money',
        'accounts_exchange_to_money'
    ),
)

cms_media_path = getattr(settings, 'CMS_PAGE_MEDIA_PATH', 'cms_page_media/')


class CMSPlaceholder(models.Model):
    """
    Model to hold content for placeholders on pages outside the CMS hierarchy.
    """
    cmscontent_placeholder = PlaceholderField('cmscontent_placeholder')
    page_identifier = models.CharField(
        max_length=255, choices=VALID_IDENTIFIER_CHOICES, unique=True)

    class Meta:
        ordering = ('page_identifier',)

    def __unicode__(self):
        return self.page_identifier


class NotificationPlugin(CMSPlugin):
    """
    Model to store data from a DjangoCMS plugin to show notifications in the
    frontend page.
    """
    CALENDAR_EVENT = 1
    ALERT = 2
    INFO = 3
    NOTIFICATION_CHOICES = (
        (CALENDAR_EVENT, _('Near event')),
        (ALERT, _('Alert')),
        (INFO, _('Information')),
    )

    notification_type = models.SmallIntegerField(choices=NOTIFICATION_CHOICES,
                                                 default=1)
    date = models.DateTimeField(null=True, blank=True)
    notice = models.CharField(max_length=100)
    info_link = models.URLField(null=True, blank=True)
    notification_link = models.URLField(null=True, blank=True)
    notification_link_label = models.CharField(max_length=20, null=True,
                                               blank=True)

    class Meta:
        ordering = ('creation_date',)

    def __unicode__(self):
        return '{0} - {1}'.format(self.notification_type, self.notice)

    def clean(self):
        """
        Override ``clean`` method to provide custom validation. The field
        ``notification_link_label`` must be set if there is a link set up.
        """
        if self.notification_link and not self.notification_link_label:
            raise ValidationError(
                _('You should provide a notification link label.'))

        super(NotificationPlugin, self).clean()


class HomepageHeader(CMSPlugin):
    """
    Model to store the text content for the homepage header.
    """
    title = models.CharField(max_length=100)
    paragraph = models.TextField()
    header_link = models.URLField(null=True, blank=True)
    button_link_text = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        ordering = ('creation_date', 'title')

    def __unicode__(self):
        return self.title

    def clean(self):
        """
        Override ``clean`` method to provide custom validation. The field
        ``button_link_text`` must be set if there is a link set up.
        """
        if self.header_link and not self.button_link_text:
            raise ValidationError(
                _('You should provide a button link text.'))

        super(HomepageHeader, self).clean()


BLOCK_ICON_CHOICES = (
    ('icon_1', 'Business'),
    ('icon_2', 'Policy maker'),
    ('icon_3', 'Communities'),
    ('icon_4', 'Folder'),
)


class HomepageBlock(CMSPlugin):
    """
    Model to store the text content for the homepage blocks.
    """
    title = models.CharField(max_length=100)
    sub_title = models.CharField(max_length=100, blank=True)
    block_link = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=100, blank=True,
                            choices=BLOCK_ICON_CHOICES)

    class Meta:
        ordering = ('creation_date', 'title')

    def __unicode__(self):
        return self.title


class SectionCarouselPlugin(CMSPlugin):
    """
    A plugin to show a carousel.
    """
    name = models.CharField(_('name'), max_length=75, default='carousel')

    def __unicode__(self):
        return self.name

    def copy_relations(self, oldinstance):
        for slide in oldinstance.sectioncarouselpluginslide_set.all():
            # instance.pk = None; instance.pk.save() is the slightly odd but
            # standard Django way of copying a saved model instance
            slide.pk = None
            slide.carousel = self
            slide.save()


class SectionCarouselPluginSlide(models.Model):
    """
    A slide of the carousel.
    """
    carousel = models.ForeignKey('SectionCarouselPlugin')
    date = models.DateField(null=True, blank=True)
    title_line_1 = models.CharField(_('title line 1'), max_length=75)
    title_line_2 = models.CharField(_('title line 2'), max_length=75)
    image = models.ImageField(_('image'), upload_to=cms_media_path)
    image_alt = models.CharField(
        _('image alt'), max_length=75, default='', blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ('order',)

    def __unicode__(self):
        return u'{0} {1}'.format(self.title_line_1, self.title_line_2)

    def get_image(self):
        """
        In order to allow template to fail gracefully, move exception handling
        up to model
        """
        try:
            if self.image.file:
                return self.image
        except Exception, e:
            return None


class SectionColumnNoticePlugin(CMSPlugin):
    """
    A plugin to show a notice text, with title, 2 paragraphs and an optional
    link.
    """
    title = models.CharField(_('title'), max_length=50, default='')
    paragraph_1 = models.TextField()
    paragraph_2 = models.TextField()
    link_target = models.URLField(null=True, blank=True)
    link_text = models.CharField(
        _('link text'), max_length=50, null=True, blank=True)

    def __unicode__(self):
        return self.title


class NewsEntry(models.Model):
    """
    A news entry to be edited by business staff. Those news will be shown then
    in the site in a `/news/` or `/blog/` page, for example.
    """
    created_by = models.ForeignKey('cyclos.User', verbose_name=_('created by'))
    creation_date = models.DateTimeField(_('creation Date'), auto_now_add=True)
    title = models.CharField(_('title'), max_length=150)
    content = models.TextField(_('content'))
    slug = autoslug.AutoSlugField(populate_from='title')

    class Meta:
        ordering = ('title', 'created_by')
        verbose_name = _('News entry')
        verbose_name_plural = _('News entries')

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news_detail', kwargs={'slug': self.slug})


class SectionColumnNewsPlugin(CMSPlugin):
    """
    A plugin to show a list of the latest news in the CMS.
    """
    title = models.CharField(_('title'), max_length=150)
    num_entries = models.IntegerField(default=3)

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return self.title


class SocialMediaLinksPlugin(CMSPlugin):
    """
    A plugin to show a CMS-configurable set of social media icons.
    """
    name = models.CharField(_('name'), max_length=75, default='social media')

    def __unicode__(self):
        return self.name

    def copy_relations(self, oldinstance):
        for link in oldinstance.socialmedialink_set.all():
            # instance.pk = None; instance.pk.save() is the slightly odd but
            # standard Django way of copying a saved model instance
            link.pk = None
            link.social_plugin = self
            link.save()


class SocialMediaLink(models.Model):
    """
    A social media link with an icon. Several of this ones can be added to a
    single ``SocialMediaLinksPlugin``.
    """
    social_plugin = models.ForeignKey('SocialMediaLinksPlugin')
    link_target = models.URLField()
    link_text = models.CharField(max_length=130, blank=True)
    css_icon_class = models.CharField(max_length=250, blank=True)

    def __unicode__(self):
        return u'{0} {1}'.format(self.social_plugin.name, self.link_target)
