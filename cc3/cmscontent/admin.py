from django.contrib import admin

from cms.admin.placeholderadmin import PlaceholderAdminMixin

from tinymce.widgets import AdminTinyMCE

from .models import CMSPlaceholder, NewsEntry


class CMSPlaceholderAdmin(PlaceholderAdminMixin, admin.ModelAdmin):
    list_display = ('page_identifier',)


class NewsEntryAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'author_email',
        'author_name',
        'creation_date'
    )
    search_fields = (
        'title',
        'content',
        'slug',
        'created_by__email',
        'created_by__username',
        'created_by__cc3_profile__first_name',
        'created_by__cc3_profile__last_name',
    )
    fields = ('creation_date', 'title', 'content')
    readonly_fields = ('creation_date',)

    def author_email(self, obj):
        return obj.created_by.email

    def author_name(self, obj):
        return obj.created_by.cc3_profile.name

    def save_model(self, request, obj, form, change):
        """
        Override the base ``save_model`` method to automatically set the author
        of the news entry to the current user.
        """
        obj.created_by = request.user

        super(NewsEntryAdmin, self).save_model(request, obj, form, change)

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Enable TinyMCE for Text Fields

        :param db_field:
        :param kwargs:
        :return:
        """
        if db_field.name == 'content':
            kwargs.pop("request", None)
            kwargs['widget'] = AdminTinyMCE(
                attrs={'cols': 60, 'rows': 5})
            return db_field.formfield(**kwargs)

        return super(NewsEntryAdmin, self).formfield_for_dbfield(
            db_field, **kwargs)

admin.site.register(CMSPlaceholder, CMSPlaceholderAdmin)
admin.site.register(NewsEntry, NewsEntryAdmin)
