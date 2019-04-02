from rest_framework import serializers
from cc3.cards.models import Card


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = (
            'card_type',
            'number',
            'card_security_code',
            'creation_date',
            'activation_date',
            'expiration_date',
            'card_security_code_blocked_until',
            'owner',
            'status',
        )
