from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from cc3.cyclos import backends
from cc3.cyclos.models import (
    User, CC3Profile, CC3Community, CyclosGroupSet, CyclosGroup)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email',)


class CommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CC3Community
        fields = ('id', 'title', 'code',)


class CyclosGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CyclosGroup
        fields = ('id', 'name')


class CyclosGroupSetSerializer(serializers.ModelSerializer):
    groups = CyclosGroupSerializer()

    class Meta:
        model = CyclosGroupSet
        fields = ('id', 'name', 'groups')


class CC3ProfileSerializer(serializers.ModelSerializer):
    # Bring in email from the user model so we can present the two in a "flat"
    # manner.
    email = serializers.EmailField(source='user.email')
    distance_km = serializers.SerializerMethodField('get_distance_km')
    available_balance = serializers.SerializerMethodField(
        'get_available_balance')
    group = serializers.SerializerMethodField('get_cyclos_group')
    community = CommunitySerializer()
    groupset = CyclosGroupSetSerializer()

    def get_distance_km(self, obj):
        """
        Only if the CC3ProfileLocationOrdering filter has been applied (or the 
        ViewableProfileManager.by_distance method used) will the distance
        property be available on the instance.
        """
        return getattr(obj, 'distance_km', None)

    def get_available_balance(self, obj):
        return obj.current_balance

    def get_cyclos_group(self, obj):
        return obj.get_cyclos_group()

    class Meta:
        model = CC3Profile
        fields = (
            "id", "is_visible", "first_name", "last_name", "email",
            "business_name", "slug", "job_title", "country", "city",
            "postal_code", "community", "latitude", "longitude", "distance_km",
            "available_balance", "phone_number",
            "mobile_number", "company_website", "company_description",
            "must_reset_password", "is_pending_closure", "community",
            "groupset", "group", "date_closure_requested", "picture",
            "picture_height", "picture_width",
        )


class TransactionActorField(serializers.CharField):
    def to_native(self, value):
        # `value` might be a User instance or it might not! Unfortunately it's
        # inconsistent because system transactions (for example) won't have an
        # associated User instance.
        if isinstance(value, User):
            profile = value.get_cc3_profile()
            buf = ''
            if profile:
                buf = profile.full_name
            if not buf:
                buf = profile.first_name
            if not buf:
                buf = value.username
            return buf
        return value


class TransactionSerializer(serializers.Serializer):
    sender = serializers.CharField()
    recipient = TransactionActorField()
    amount = serializers.DecimalField(
        min_value=0.01, max_digits=10, decimal_places=2)
    created = serializers.DateTimeField()
    description = serializers.CharField()
    transfer_id = serializers.IntegerField()


class PayDirectSerializer(serializers.Serializer):
    """
    Serializer used to send a payment.

    Sender is the logged in user.
    """
    amount = serializers.DecimalField(
        required=True, min_value=0.01, max_digits=10, decimal_places=2)
    recipient = serializers.PrimaryKeyRelatedField(
        required=True, many=False, queryset=CC3Profile.viewable.all())
    description = serializers.CharField(
        required=True, max_length=255)

    def validate_amount(self, attrs, source):
        amount = attrs[source]
        sender = self.context['user']
        available_balance = backends.get_account_status(
            sender.username).accountStatus.availableBalance

        if amount > available_balance:
            raise serializers.ValidationError(
                _(u'You do not have sufficient credit to complete the payment'))

        # TODO: Update to validate integer for systems with integer currencies

        return attrs

    def validate_recipient(self, attrs, source):
        profile = attrs[source]
        pending_can_pay = getattr(
            settings, 'CYCLOS_PENDING_MEMBERS_CAN_PAY', True)

        if not profile.has_full_account() and not pending_can_pay:
            raise serializers.ValidationError(
                _(u"You cannot pay this member as their account "
                  u"is still pending."))
        return attrs
