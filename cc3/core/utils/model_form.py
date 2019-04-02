# No longer works with Django 1.8 as fields or exclude needs to be defined
# use modelform_factory with model._meta.get_all_field_names() as a basis
#  - see cc3.files.utils

# from django import forms
#
#
# def model_to_modelform(model):
#     """
#     #http://www.agmweb.ca/2010-03-24-creating-a-modelform-dynamically/
#     :param model: content_type to be used for the form
#     :return: ModelForm for the model
#     """
#     meta = type('Meta', (), {"model": model, })
#     modelform_class = type('modelform', (forms.ModelForm,), {"Meta": meta})
#     return modelform_class
