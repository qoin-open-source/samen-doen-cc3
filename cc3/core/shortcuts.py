from django.shortcuts import render_to_response as django_render_to_response
from django.template import RequestContext


def render_to_response(template, dictionary=None, request=None, **kwargs):
    context_instance = None
    if request:
        context_instance = RequestContext(request)
    return django_render_to_response(
        template, dictionary, context_instance=context_instance, **kwargs)
