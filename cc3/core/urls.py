from django.conf import settings
from django.conf.urls import include, patterns, url
from django.http import HttpResponse
from cc3.core.views import upload_progress


urlpatterns = patterns(
    '',
    url(r'^admin/(?P<app>[-\w]+)/(?P<model>[-\w]+)/xls/$',
        include('cc3.excelexport.urls')),
    url('^uploads/upload_progress/$', upload_progress, name='upload_progress'),
    url(r'^', include('cc3.invoices.urls')),
)

if getattr(settings, "ROBOTS_DISALLOW", False):
    urlpatterns += patterns(
        url(r'^robots.txt$', lambda r: HttpResponse(
            "User-agent: *\nDisallow: /", content_type="text/plain")),
    )
