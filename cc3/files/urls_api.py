from django.conf.urls import patterns, url
#
from .views_api import FileServiceUserLoginView, UploadFileView, ProcessFileTypeSetView


urlpatterns = patterns(
    '',
    url(r'^login/$', FileServiceUserLoginView.as_view(),
        name='api_files_login'),
    # POST only: {'name': 'stadlander', 'password': 'abcdefgh'}

    url(r'^upload/$', UploadFileView.as_view(),
        name='api_files_upload'),
    # POST only (multipart):
    # DATA: {'file_type': 'huurcontract', 'test': True} # test = True, only test, test = False or None, full upload
    # FILES: {'document', doc}

    url(r'^process/$', ProcessFileTypeSetView.as_view(),
        name='api_files_process'),
    # POST only: {'name': 'stadlander'}

)
