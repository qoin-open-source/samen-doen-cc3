from django.forms import ModelForm

from .models import Card, CardNumber

from ajax_select import make_ajax_field


class CardForm(ModelForm):

    class Meta:
        model = Card
        fields = (
            'card_type', 'number', 'card_security_code',
            'activation_date', 'expiration_date',
            'card_security_code_blocked_until', 'owner', 'status')

    number = make_ajax_field(CardNumber, 'number', 'number')
