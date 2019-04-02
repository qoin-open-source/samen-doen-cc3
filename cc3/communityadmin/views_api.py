from django.shortcuts import get_object_or_404, get_list_or_404

from rest_framework import parsers, status, views
from rest_framework.response import Response

from cc3.core.api import permissions
from cc3.marketplace.models import Ad, AdImage
from cc3.marketplace.serializers import AdImageSerializer


class CommunityAdImageListView(views.APIView):
    """
    Returns a list of ``AdImage`` objects for the current community.

    Endpoint: /api/comm/ad_images/
    """
    parser_classes = (parsers.MultiPartParser,)
    permission_classes = (permissions.IsCommunityAdmin,)

    def get(self, request, format=None):
        ad_images = get_list_or_404(
            AdImage,
            ad__created_by__community=request.user.get_admin_community())
        serializer = AdImageSerializer(ad_images)

        return Response(serializer.data)


class CommunityAdImagesView(views.APIView):
    """
    Returns a list of ``AdImage`` objects related to a specific ``Ad`` or
    creates a new one.

    Endpoint: /api/comm/ad_images/{ad.pk}/
    """
    parser_classes = (parsers.MultiPartParser,)
    permission_classes = (permissions.IsCommunityAdmin,)

    def get(self, request, ad, format=None):
        ad_images = get_list_or_404(
            AdImage,
            ad__created_by__community=request.user.get_admin_community(),
            ad=ad)
        serializer = AdImageSerializer(ad_images)

        return Response(serializer.data)

    def post(self, request, ad, format=None):
        """
        Uploads a new ``AdImage`` related to an existent ``Ad``.
        """
        ad = get_object_or_404(Ad, pk=ad)

        request.data['ad'] = ad.pk
        request.data['user_created'] = self.request.user.pk
        request.data['caption'] = self.request.FILES['image'].name

        serializer = AdImageSerializer(
            data=request.data, files=request.FILES)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST)
