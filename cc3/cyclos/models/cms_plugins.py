from django.db import models

# WARNING HACK to enable very old CommunityPluginModel to compile.
# TO BE REMOVED?
from djangocms_text_ckeditor.utils import plugin_tags_to_id_list
# from cms.plugins.text.utils import plugin_tags_to_id_list

from cms.models.pluginmodel import CMSPlugin
from .community import CC3Community


class CommunityPluginModel(CMSPlugin):
    body = models.TextField(blank=True)

    class Meta:
        app_label = 'cyclos'

    def copy_relations(self, oldinstance):
        for community_message in oldinstance.communitymessage_set.all():
            community_message.pk = None
            community_message.plugin = self
            community_message.save()

    def clean_plugins(self):
        ids = plugin_tags_to_id_list(self.body)
        plugins = CMSPlugin.objects.filter(parent=self)
        for plugin in plugins:
            if not plugin.pk in ids:
                # Delete plugins that are not referenced in the text anymore.
                plugin.delete()


class CommunityMessage(models.Model):
    plugin = models.ForeignKey('CommunityPluginModel')
    community = models.ForeignKey(CC3Community, blank=True, null=True)
    body = models.TextField(blank=True)

    class Meta:
        app_label = 'cyclos'

    def __unicode__(self):
        return "Message for {community}".format(community=self.community)
