import json

from datetime import date
from django.http import HttpResponse


# https://docs.djangoproject.com/en/1.5/topics/class-based-views/generic-editing/
class RegistrationAjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Registration specific version...
    """
    def render_to_json_response(self, context, **response_kwargs):
        data = json.dumps(context)
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)

    def form_invalid(self, form):

        response = super(RegistrationAjaxableResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            return self.render_to_json_response(form.errors, status=400)
        else:
            return response

    def form_valid(self, request, form):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super(RegistrationAjaxableResponseMixin, self).form_valid(request, form)
        if request.is_ajax():
            data = {
                'success': True,
            }
            return self.render_to_json_response(data)
        else:
            return response


def calculate_age(born):
    today = date.today()
    try: 
        birthday = born.replace(year=today.year)
    except ValueError: # raised when birth date is February 29 and the current year is not a leap year
        birthday = born.replace(year=today.year, day=born.day-1)
    if birthday > today:
        return today.year - born.year - 1
    else:
        return today.year - born.year
