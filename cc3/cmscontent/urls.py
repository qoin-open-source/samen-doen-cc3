from django.conf.urls import patterns, url

from .views import NewsEntryDetailView, NewsEntryListView

urlpatterns = patterns(
    '',
    url(r'^news/$', NewsEntryListView.as_view(), name='news_list'),
    url(r'^news/(?P<slug>[-\w]+)/$', NewsEntryDetailView.as_view(),
        name='news_detail'),
)
