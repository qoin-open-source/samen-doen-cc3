from django.shortcuts import get_object_or_404, get_list_or_404

from rest_framework import (
    generics, filters, mixins, parsers, permissions, status, views, viewsets)
from rest_framework.authentication import (
    BasicAuthentication, SessionAuthentication)
from rest_framework.response import Response

from oauth2_provider.ext.rest_framework import OAuth2Authentication

from cc3.core.api import permissions as cc3_permissions
from cc3.cyclos.models import CC3Profile, User
from .common import AD_STATUS_ACTIVE
from .filters import AdFilter
from .models import Ad, AdImage, AdType, PreAdImage
from .serializers import (
    AdTypeSerializer, AdSerializer, AdImageSerializer, PreAdImageSerializer)


class MarketplaceAdImageListView(views.APIView):
    """
    Returns a list of ``AdImage`` objects for the current community.

    Endpoint: /api/marketplace/ad_images/
    """
    authentication_classes = (
        SessionAuthentication, BasicAuthentication, OAuth2Authentication)
    parser_classes = (parsers.MultiPartParser,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        ad_images = get_list_or_404(
            AdImage,
            ad__created_by__community=request.user.get_community())
        serializer = AdImageSerializer(ad_images)

        return Response(serializer.data)


class MarketplaceAdImagesView(views.APIView):
    """
    Returns a list of ``AdImage`` objects related to a specific ``Ad`` or
    creates a new one.

    Endpoint: /api/marketplace/ad_images/{ad.pk}/
    """
    authentication_classes = (
        SessionAuthentication, BasicAuthentication, OAuth2Authentication)
    parser_classes = (parsers.MultiPartParser, parsers.FormParser)
    permission_classes = (cc3_permissions.IsAdManager,)

    def get(self, request, ad=None, format=None):
        # Hack to make sure we have a cyclos User.
        user = User.objects.get(pk=self.request.user.pk)
        ad_images = get_list_or_404(
            AdImage,
            ad__created_by__community=user.get_community(),
            ad=ad)
        serializer = AdImageSerializer(ad_images)

        return Response(serializer.data)

    def delete(self, request, ad=None, format=None):
        image_id = request.data['id']
        if ad:
            img_cls = AdImage
        else:
            img_cls = PreAdImage

        try:
            images = img_cls.objects.filter(id=image_id)
        except ValueError, e:
            images = None

        if not images:
            images = img_cls.objects.filter(caption=image_id)

        images.delete()
        return Response('')

    def post(self, request, ad=None, format=None):
        """
        Uploads a new ``AdImage``

        An Ad can either already exist (in which case the AdImage is created and linked to the Ad)
        or the Ad is still being authored by the user. In this case the image is stored as a PreAdImage,
        which is only saved as an AdImage once the user actually saves the Ad.
        """
        request.data['user_created'] = self.request.user.pk

        if not request.data.get('caption'):
            request.data['caption'] = self.request.data['image'].name

        if ad:
            ad = get_object_or_404(Ad, pk=ad)
            request.data['ad'] = ad.pk
            serializer = AdImageSerializer(data=request.data)
        else:
            serializer = PreAdImageSerializer(data=request.data)

        if serializer.is_valid():
            image_object = serializer.save()
            if ad:
                returned_dict = {
                    "id": image_object.id,
                    "image": image_object.image.name,
                    "image_url": image_object.image.url,
                    "user_created": image_object.user_created_id,
                    "ad": image_object.ad_id,
                    "caption": image_object.caption,
                }
            else:
                returned_dict = {
                    "image": image_object.image.name,
                    "user_created": image_object.user_created.id,
                    "caption": image_object.caption
                }
            return Response(returned_dict, status=status.HTTP_201_CREATED)
        else:
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdTypeListAPIView(generics.ListAPIView):
    model = AdType
    serializer_class = AdTypeSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.user.is_superuser:
            return AdType.objects.all()
        else:
            return AdType.objects.filter(active=True)


class AdAPIViewSet(viewsets.ViewSet, generics.GenericAPIView,
        mixins.CreateModelMixin, mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin, mixins.DestroyModelMixin):
    """
    Handles retrieve, update and delete views for Ad objects.
    """
    model = Ad
    serializer_class = AdSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """
        Superusers can see and edit anything.

        Normal users can see active ads.

        Anything else is denied.
        """
        if self.request.user.is_superuser:
            return Ad.objects.all()

        if self.request.method in ['GET', 'OPTIONS', 'HEAD']:
            return Ad.objects.filter(status=AD_STATUS_ACTIVE)

        # Here we are not a superuser and we are dealing with data-altering
        # methods. The user must only be able to do this to their own ads.
        profile = get_object_or_404(CC3Profile, user__pk=self.request.user.pk)
        return Ad.objects.filter(created_by=profile)

    def pre_save(self, obj):
        profile = get_object_or_404(CC3Profile, user__pk=self.request.user.pk)
        obj.created_by = profile


class AdListAPIView(generics.ListAPIView):
    """
    Return list of Ads, optionally filtered by account.
    """
    model = Ad
    serializer_class = AdSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = (
        filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    filter_class = AdFilter
    search_fields = ('title', 'description',)
    ordering_fields = '__all__'

    def get_queryset(self):
        if 'pk' in self.kwargs:
            profile = get_object_or_404(CC3Profile, pk=self.kwargs['pk'])
            qs = Ad.objects.filter(created_by=profile.user)
        else:
            qs = Ad.objects.all()

        if not self.request.user.is_superuser:
            qs = qs.filter(status=AD_STATUS_ACTIVE)
        return qs
