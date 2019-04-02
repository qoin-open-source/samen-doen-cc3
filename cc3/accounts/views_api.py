from rest_framework import filters, status, permissions, views, viewsets
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response

from cc3.cyclos import backends
from cc3.cyclos.models import CC3Profile, User
from cc3.core.api.permissions import HasCompletedProfile, IsSuperuserOrReadOnly
from cc3.marketplace.models import AdPaymentTransaction
from cc3.cyclos.common import TransactionException

from .exceptions import APITransactionException
from .filters import CC3ProfileLocationOrdering
from .serializers import (
    CC3ProfileSerializer, TransactionSerializer, PayDirectSerializer)


class AccountsAPIViewSet(viewsets.ViewSet, ListAPIView, RetrieveUpdateAPIView):
    model = CC3Profile
    serializer_class = CC3ProfileSerializer
    permission_classes = (IsSuperuserOrReadOnly,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter,
                       CC3ProfileLocationOrdering)  # Must come last.
    search_fields = (
        'first_name', 'last_name', 'business_name', 'user__email', 'address',
        'city', 'postal_code', 'company_description',
    )
    ordering_fields = '__all__'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return CC3Profile.viewable.all()
        else:
            return CC3Profile.viewable.filter(is_visible=True)


class AccountAPIView(RetrieveUpdateAPIView):
    """
    Endpoint for viewing and editing one's own account details.


    Login:

    curl -H "Content-Type: application/json" -d '{"username":"username/email",
    "password":"password"}' http://localhost:8014/api/auth/login/

    returns: {"auth_token": "64e96caae93ab6262f712525c7f33b9b28a6406a"}

    Use token in header:
    $ curl -H "Authorization: Token 64e96caae93ab6262f712525c7f33b9b28a6406a"
    -H "Content-Type: application/json"
    http://localhost:8014/api/rekeningen/account/

    Returns:
    {
        "id": 144,
        "is_visible": false,
        "first_name": "Mari\u00ebt",
        "last_name": "IJdens",
        "email": "stephen@maxgatedigital.com",
        "business_name": "SVRZ",
        "slug": "de-schutze",
        "job_title": "",
        "country": "",
        "city": "Tholen",
        "postal_code": "4691 ZA",
        "community": {
            "id": 1,
            "title": "Tholen",
            "code": "THOL"
        },
        "latitude": "51.49500000000000",
        "longitude": "4.29309999999900",
        "distance_km": null,
        "available_balance": "-6691.000000",
        "registration_number": "",
        "phone_number": "0888871000",
        "mobile_number": "",
        "company_website": "http://www.svrz.nl/",
        "company_description": "SVRZ biedt zorg in Zeeland. Vanuit acht
            zorgcentra en talloze kleinschalige woningen in de wijk of het dorp.
            Aan mensen met dementie of lichamelijke beperkingen. 2700
            medewerkers zorgen voor kwalitatief, goede zorg die aansluit bij
            de wensen van de cli\u00ebnten. Zij staan centraal",
        "must_reset_password": false,
        "is_pending_closure": false,
        "groupset": {
            "id": 2, "name":
            "Positoos groupset",
            "groups": [{
                "id": 5,
                "name": "Consumenten"
            },{
                "id": 12,
                "name": "Organisaties"
            }, {
                "id": 13,
                "name": "Goede Doelen"
            }, {
                "id": 14,
                "name": "Instituties"
            }]
        },
        "group": "Instituties",
        "date_closure_requested": null,
        "picture": "profile_pictures/144_SVRZ logo.png",
        "picture_height": 920,
        "picture_width": 920
    }
    """
    model = CC3Profile
    serializer_class = CC3ProfileSerializer
    permission_classes = (permissions.IsAuthenticated, )

    def get_object(self, queryset=None):
        # Hack to make sure we have a cyclos User.
        user = User.objects.get(pk=self.request.user.pk)
        return CC3Profile.viewable.get(user=user)


class TransactionsListAPIView(ListAPIView):
    """
    Login:

    curl -H "Content-Type: application/json" -d '{"username":"username/email",
    "password":"password"}' http://localhost:8014/api/auth/login/

    returns: {"auth_token": "64e96caae93ab6262f712525c7f33b9b28a6406a"}

    Use token in header:
    $ curl -H "Authorization: Token 64e96caae93ab6262f712525c7f33b9b28a6406a"
    -H "Content-Type: application/json"
    http://localhost:8014/api/rekeningen/transactions/

    returns 10 transactions, and total number - add ?page=N for next page
    returns:
    {
      "count": 15,
      "next": "http://localhost:8014/api/rekeningen/transactions/?page=2",
      "previous": null,
      "results": [
        {
          "sender": "sd6qoinorg",
          "recipient": "gert meeder",
          "amount": "-10.000000",
          "created": "2015-08-19T10:31:32+01:00",
          "description": "Positoos gespaard bij winkelier, ondernemer of ....",
          "transfer_id": 8447
        },
        {
          "sender": "gert meeder",
          "recipient": "sd6qoinorg",
          "amount": "22.000000",
          "created": "2015-08-19T10:31:18+01:00",
          "description": "Positoos verzilverd",
          "transfer_id": 8446
        },
        {
          "sender": "sd6qoinorg",
          "recipient": "gert meeder",
          "amount": "-2.000000",
          "created": "2015-08-19T10:31:04+01:00",
          "description": "Positoos gespaard bij winkelier, ondernemer of ....",
          "transfer_id": 8445
        },
        {
          "sender": "2693THOL",
          "recipient": "sd6qoinorg",
          "amount": "6.000000",
          "created": "2015-08-04T16:36:31+01:00",
          "description": "Positoos verzilverd",
          "transfer_id": 8222
        },
        {
          "sender": "2693THOL",
          "recipient": "sd6qoinorg",
          "amount": "10.000000",
          "created": "2015-08-04T16:36:09+01:00",
          "description": "Positoos verzilverd",
          "transfer_id": 8221
        },
        {
          "sender": "sd6qoinorg",
          "recipient": "THOL 2693THOL (THOL 2693THOL)",
          "amount": "-1000.000000",
          "created": "2015-08-04T16:35:56+01:00",
          "description": "Positoos gespaard bij winkelier, ondernemer of ....",
          "transfer_id": 8219
        },
        {
          "sender": "sd6qoinorg",
          "recipient": "THOL 2693THOL (THOL 2693THOL)",
          "amount": "-100.000000",
          "created": "2015-08-04T16:33:41+01:00",
          "description": "Positoos gespaard bij winkelier, ondernemer of ....",
          "transfer_id": 8217
        },
        {
          "sender": "sd6qoinorg",
          "recipient": "THOL 2693THOL (THOL 2693THOL)",
          "amount": "-110.000000",
          "created": "2015-08-04T16:32:48+01:00",
          "description": "Positoos gespaard bij winkelier, ondernemer of ....",
          "transfer_id": 8215
        },
        {
          "sender": "sd6qoinorg",
          "recipient": "Katrien Duck",
          "amount": "-100.000000",
          "created": "2015-07-30T09:03:35+01:00",
          "description": "test betaling",
          "transfer_id": 8207
        },
        {
          "sender": "sd6qoinorg",
          "recipient": "jan Hoek (jan Hoek)",
          "amount": "-100.000000",
          "created": "2015-07-30T09:02:09+01:00",
          "description": "Positoos gespaard bij winkelier, ondernemer of ....",
          "transfer_id": 8206
        }
      ]
    }

    """
    permission_classes = (permissions.IsAuthenticated,)
    # TODO: Use a custom TransactionSerializer to return profile type
    # and related image (if profile has no image)
    serializer_class = TransactionSerializer
    paginate_by = 10

    def list(self, request, *args, **kwargs):
        user = request.user
        direction = request.QUERY_PARAMS.get('direction', 'desc')

        pageable_transactions = backends.transactions(
            user.username,
            direction=direction
        )

        # Switch between paginated or standard style responses
        page = self.paginate_queryset(pageable_transactions)
        if page is not None:
            serializer = self.get_pagination_serializer(page)
        else:
            serializer = self.get_serializer(pageable_transactions, many=True)

        return Response(serializer.data)


class PayDirectAPIView(views.APIView):
    """
    Login:

    curl -H "Content-Type: application/json"
    -d '{"username":"sl13qoinorg", "password":"password"}'
    http://localhost:8014/api/auth/login/

    returns: {"auth_token": "1c753c829b128a7c1c741fc9d500225e4716e85c"}

    Use token in header:
    $ curl -H "Authorization: Token 1e8402fc14778ae9119199803ef633826001ba69"
    -d '{"amount": 12, "description":"abc", "recipient":204}'
    -H "Content-Type: application/json"
    http://localhost:8014/api/rekeningen/pay_direct/

    """
    permission_classes = (permissions.IsAuthenticated, HasCompletedProfile,)
    serializer_class = PayDirectSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(
            data=request.data, context={'user': request.user})
        if serializer.is_valid():
            # Hack to make sure we have a cyclos User an auth one otherwise
            # AdPaymentTransaction complains.
            sender = User.objects.get(pk=request.user.pk)
            amount = serializer.object['amount']
            description = serializer.object['description']
            receiver = serializer.object['recipient'].user

            # Make the payment.
            try:
                transaction = backends.user_payment(
                    sender, receiver, amount, description)
                # Log the payment.
                AdPaymentTransaction.objects.create(
                    title=description,
                    amount=amount,
                    sender=sender,
                    receiver=receiver,
                    transfer_id=transaction.transfer_id
                )
            except TransactionException:
                raise APITransactionException()

            return Response(request.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
