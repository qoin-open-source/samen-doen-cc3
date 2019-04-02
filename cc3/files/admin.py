from django.contrib import admin

from cc3.excelexport.admin import admin_action_export_xls

from .models import FileType, FileTypeSet, Format, Upload, FileServiceUser, UploadInstance


class FileTypeAdmin(admin.ModelAdmin):
    list_display = ('description', 'format', 'process_model', 'instance_identifier', 'filetypeset')


class FormatAdmin(admin.ModelAdmin):
    list_display = ('description', 'mime_type', 'extension')


class UploadAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('file', 'file_type', 'date_created', 'user_created', 'status')


class UploadInstanceAdmin(admin.ModelAdmin):
    actions = [admin_action_export_xls]
    list_display = ('content_object', 'status', 'upload')


class FileServiceUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_addresses')


admin.site.register(FileType, FileTypeAdmin)
admin.site.register(FileTypeSet)
admin.site.register(Format, FormatAdmin)
admin.site.register(Upload, UploadAdmin)
admin.site.register(UploadInstance, UploadInstanceAdmin)
admin.site.register(FileServiceUser, FileServiceUserAdmin)
