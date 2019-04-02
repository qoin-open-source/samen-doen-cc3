import logging

from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from cc3.cyclos.models import CC3Community

from .models import Dashboard, Graph


LOG = logging.getLogger('__file__')


class GraphInlineAdmin(admin.TabularInline):
    model = Graph


class NewTitleChangeList(ChangeList):
    def __init__(self, *args, **kwargs):
        super(NewTitleChangeList, self).__init__(*args, **kwargs)
        self.title = _(u"Select Dashboard")


class DashboardAdmin(admin.ModelAdmin):
    inlines = [GraphInlineAdmin, ]
    list_display = ('title', 'active',)
    save_on_top = True

    def get_changelist(self, request, **kwargs):
        return NewTitleChangeList

    def changelist_view(self, request, extra_context=None):
        self.community_filter_code = request.session.get(
            'stats_community_code', '')
        extra_context = extra_context or {}
        all_dashes = Dashboard.objects.filter(active=True)
        current_id = request.GET.get('id', None)
        try:
            extra_context['current_dash'] = int(current_id)
        except:
            pass
        extra_context['all_dashes'] = all_dashes
        extra_context['communities'] = CC3Community.objects.all()
        extra_context['community_filter_code'] = self.community_filter_code
        return super(DashboardAdmin, self).changelist_view(
            request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super(DashboardAdmin, self).get_queryset(request)
        # community_code = request.session.get('stats_community_code', '')

        # extra is discouraged, but need a later verion of django for Valeue
        # return qs.annotate(community_filter_code=Value('THOL'))
        if hasattr(self, 'community_filter_code'):
            return qs.extra(select={
                'community_filter_code': "'{0}'".format(
                    self.community_filter_code)})
        return qs

    def update_filter_view(self, request):
        """ Store ccode (community code) for community filter in session
        and refresh page """
        community_code = request.GET.get('ccode', '')
        refresh_url = request.GET.get('next')
        request.session['stats_community_code'] = community_code
        return HttpResponseRedirect(refresh_url)

    def get_urls(self):
        urls = super(DashboardAdmin, self).get_urls()
        custom_urls = patterns(
            '',
            url(r'^update_filter/$',
                self.admin_site.admin_view(self.update_filter_view),
                name='admin_update_filter'),
        )
        return custom_urls + urls

admin.site.register(Dashboard, DashboardAdmin)
