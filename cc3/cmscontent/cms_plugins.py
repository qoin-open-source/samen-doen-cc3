from django.contrib.admin import StackedInline
from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import (
    HomepageBlock, HomepageHeader, NotificationPlugin, NewsEntry,
    SectionCarouselPlugin, SectionCarouselPluginSlide, SectionColumnNewsPlugin,
    SectionColumnNoticePlugin, SocialMediaLink, SocialMediaLinksPlugin)


class CMSNotificationPlugin(CMSPluginBase):
    """
    DjangoCMS plugin to show notifications in the frontend.
    """
    model = NotificationPlugin
    name = _('Notification plugin')
    render_template = 'cmscontent/notification.html'

    def render(self, context, instance, placeholder):
        context['instance'] = instance
        return context


class CMSHomepageHeaderPlugin(CMSPluginBase):
    """
    DjangoCMS plugin to show a header in the homepage.
    """
    model = HomepageHeader
    name = _('Homepage header')
    render_template = 'cmscontent/homepage_header.html'

    def render(self, context, instance, placeholder):
        context['instance'] = instance
        return context


class CMSHomepageBlockPlugin(CMSPluginBase):
    """
    DjangoCMS plugin to show a block on the homepage.
    """
    model = HomepageBlock
    name = _('Homepage block')
    render_template = 'cmscontent/homepage_block.html'

    def render(self, context, instance, placeholder):
        context['instance'] = instance
        return context


class SectionCarouselPluginSlideInline(StackedInline):
    """
    Slides to be added to the ``CMSSectionCarouselPlugin``.
    """
    model = SectionCarouselPluginSlide


class CMSSectionCarouselPlugin(CMSPluginBase):
    """
    DjangoCMS plugin to show a carousel with dynamic images and text.
    """
    model = SectionCarouselPlugin
    name = _('Section Carousel')
    render_template = 'cmscontent/section_carousel.html'
    inlines = [SectionCarouselPluginSlideInline]

    def render(self, context, instance, placeholder):
        context['instance'] = instance
        return context


class CMSSectionColumnNoticePlugin(CMSPluginBase):
    """
    DjangoCMS plugin to show a column of text in homepage.
    """
    model = SectionColumnNoticePlugin
    name = _('Homepage notice column')
    render_template = 'cmscontent/homepage_notice_column.html'

    def render(self, context, instance, placeholder):
        context['instance'] = instance
        return context


class CMSSectionColumnNewsPlugin(CMSPluginBase):
    """
    DjangoCMS plugin to show a column of latest news list in homepage.
    """
    model = SectionColumnNewsPlugin
    name = _('Homepage news list column')
    render_template = 'cmscontent/homepage_news_column.html'

    def render(self, context, instance, placeholder):
        num_entries = instance.num_entries or 3
        context['news_list'] = NewsEntry.objects.order_by('-creation_date')[:num_entries]
        context['instance'] = instance
        return context


class SocialMediaLinkPluginLink(StackedInline):
    """
    A social media link unit for the ``CMSSocialMediaLinksPlugin``.
    """
    model = SocialMediaLink


class CMSSocialMediaLinksPlugin(CMSPluginBase):
    """
    DjangoCMS plugin to show a set of social media links.
    """
    model = SocialMediaLinksPlugin
    name = _('Social Media links')
    render_template = 'cmscontent/social_media_links.html'
    inlines = [SocialMediaLinkPluginLink]

    def render(self, context, instance, placeholder):
        context['instance'] = instance
        return context


plugin_pool.register_plugin(CMSNotificationPlugin)
plugin_pool.register_plugin(CMSHomepageHeaderPlugin)
plugin_pool.register_plugin(CMSHomepageBlockPlugin)
plugin_pool.register_plugin(CMSSectionCarouselPlugin)
plugin_pool.register_plugin(CMSSectionColumnNoticePlugin)
plugin_pool.register_plugin(CMSSectionColumnNewsPlugin)
plugin_pool.register_plugin(CMSSocialMediaLinksPlugin)
