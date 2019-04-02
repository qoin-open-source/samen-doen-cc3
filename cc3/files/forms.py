import re

from django import forms


class FileTypeSetForm(forms.Form):

    name = forms.CharField(required=True)

    def clean_name(self):
        data = self.cleaned_data['name'].lower()
        if not re.match(r'[A-z]+', data):
            raise forms.ValidationError('Alpha characters only.')

        return data