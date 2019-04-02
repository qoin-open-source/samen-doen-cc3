from rest_framework import serializers

from .models import Ad, AdType, AdImage, PreAdImage


class AdTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdType
        fields = ('id', 'code', 'title', 'active',)


class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = (
            'id', 'title', 'adtype', 'description', 'price', 'price_option',
            'barter_euros', 'views', 'date_created', 'status', 'category',
        )


class AdImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()
#    image_url = serializers.SerializerMethodField('get_image_url')

#    def get_image_url(self, obj):
#        return obj.image.url if obj.image else None

    class Meta:
        model = AdImage
        fields = ('id', 'image', 'user_created', 'ad', 'caption')


class PreAdImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()

    class Meta:
        model = PreAdImage
        fields = ('image', 'user_created', 'caption')
