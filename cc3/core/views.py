import logging

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseServerError
from django.template import Context, RequestContext, loader
from django.views.generic import TemplateView

LOG = logging.getLogger(__name__)


class DirectTemplateView(TemplateView):
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super(DirectTemplateView, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value
        return context


def upload_progress(request):
    """
    Return JSON object with information about the progress of an upload.
    """
    progress_id = ''
    if 'X-Progress-ID' in request.GET:
        progress_id = request.GET['X-Progress-ID']
    elif 'X-Progress-ID' in request.META:
        progress_id = request.META['X-Progress-ID']
    LOG.debug("upload_progress() progress_id {0}".format(progress_id))
    if progress_id:
        from django.utils import json
        cache_key = "{0}_{1}".format(request.META['REMOTE_ADDR'], progress_id)
        LOG.debug("upload_progress() cache_key {0}".format(cache_key))
        data = cache.get(cache_key)
        LOG.debug("upload_progress() data {0}".format(data))
        return HttpResponse(json.dumps(data))
    else:
        return HttpResponseServerError(
            'Server Error: You must provide X-Progress-ID header or query '
            'param.')


def server_error(request, template_name='500.html'):
    """Special server error handler that uses RequestContext if possible.
    
    To use, put `handler500 = 'cc3.views.server_error'` in urls.py.
    """
    # You need to create a 500.html template.
    template = loader.get_template(template_name)
    try:
        return HttpResponseServerError(
            template.render(RequestContext(request, {})))
    except:
        return HttpResponseServerError(
            template.render(Context({})))
