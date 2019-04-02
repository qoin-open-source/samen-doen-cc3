from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
#from cms.plugins.text.settings import USE_TINYMCE
#from cms.plugins.text.widgets.wymeditor_widget import WYMEditor
from djangocms_text_ckeditor.utils import plugin_tags_to_user_html

from django.forms.fields import CharField
from django.contrib import admin
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned

from .models import CommunityPluginModel, CommunityMessage, CC3Profile


class CommunityPluginInline(admin.TabularInline):
    model = CommunityMessage
    extra = 1

    def get_editor_widget(self, plugins):
        """
        Returns the Django form Widget to be used for
        the text area
        """
        if USE_TINYMCE and "tinymce" in settings.INSTALLED_APPS:
            from cms.plugins.text.widgets.tinymce_widget import TinyMCEEditor
            return TinyMCEEditor(installed_plugins=plugins)
        else:
            return WYMEditor(installed_plugins=plugins)

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'body':
            plugins = []
            widget = self.get_editor_widget(plugins)
            return db_field.formfield(widget=widget)
        return super(CommunityPluginInline, self).formfield_for_dbfield(
            db_field, **kwargs)


class CommunityPlugin(CMSPluginBase):
    model = CommunityPluginModel
    render_template = "community_plugin.html"
    inlines = [CommunityPluginInline]

    def get_editor_widget(self, request, plugins):
        """
        Returns the Django form Widget to be used for
        the text area
        """
        if USE_TINYMCE and "tinymce" in settings.INSTALLED_APPS:
            from cms.plugins.text.widgets.tinymce_widget import TinyMCEEditor
            return TinyMCEEditor(installed_plugins=plugins)
        else:
            return WYMEditor(installed_plugins=plugins)

    def get_form_class(self, request, plugins):
        """
        Returns a subclass of Form to be used by this plugin
        """
        # We avoid mutating the Form declared above by subclassing
        class TextPluginForm(self.form):
            pass
        widget = self.get_editor_widget(request, plugins)
        TextPluginForm.declared_fields["body"] = CharField(
            widget=widget, required=False)
        return TextPluginForm

    def get_form(self, request, obj=None, **kwargs):
        plugins = plugin_pool.get_text_enabled_plugins(
            self.placeholder, self.page)
        form = self.get_form_class(request, plugins)
        kwargs['form'] = form  # Override standard form
        return super(CommunityPlugin, self).get_form(request, obj, **kwargs)

    def render(self, context, instance, placeholder):
        context.update({
            'body': plugin_tags_to_user_html(
                instance.body, context, placeholder),
            'placeholder': placeholder,
            'object': instance
        })
        context['message'] = ''
        community = None

        user = context['request'].user
        if user.is_authenticated():
            try:
                cc3_profile = CC3Profile.viewable.get(
                    user=context['request'].user)
                community = cc3_profile.community
            except CC3Profile.DoesNotExist:
                pass

        if community:
            try:
                message = instance.communitymessage_set.get(community=community)
                context['message'] = message.body
            except CommunityMessage.DoesNotExist:
                pass
            except MultipleObjectsReturned:
                message = instance.communitymessage_set.filter(
                    community=community).order_by('-pk')[0]
                context['message'] = message.body
        else:
            context['message'] = instance.body

        return context

    def save_model(self, request, obj, form, change):
        obj.clean_plugins()
        super(CommunityPlugin, self).save_model(request, obj, form, change)


plugin_pool.register_plugin(CommunityPlugin)
