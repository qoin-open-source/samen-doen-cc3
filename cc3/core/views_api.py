from rest_framework import generics, permissions

from .models import Category
from .serializers import CategorySerializer


class CategoriesListAPIView(generics.ListAPIView):
    model = Category
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Category.objects.all()
        else:
            return Category.objects.filter(active=True)
