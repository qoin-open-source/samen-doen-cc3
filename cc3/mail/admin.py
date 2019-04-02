from django.contrib import admin

from .models import MailMessage, Attachment


class MailMessageAdmin(admin.ModelAdmin):
    list_display = ('get_type_display', 'subject', 'lang')
    filter_horizontal = ['attachments']


admin.site.register(Attachment)
admin.site.register(MailMessage, MailMessageAdmin)
