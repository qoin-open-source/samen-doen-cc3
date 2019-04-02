from django.conf.urls import *

from cc3.excelexport.views import admin_export_xls

urlpatterns = patterns('',
    (r'^$', admin_export_xls),
)
