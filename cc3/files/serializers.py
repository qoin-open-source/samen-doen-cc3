import logging

from rest_framework import serializers

from .models import Upload, FileType
from .utils import validate_csv_file

LOG = logging.getLogger(__name__)


class UploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField()
    file_type = serializers.SlugRelatedField(
        slug_field='description', queryset=FileType.objects.all()
    )

    class Meta:
        model = Upload
        fields = ('file_type', 'file', 'user_created')

    def validate(self, attrs):
        """
        Check that the file contains valid data for the file_type.
        """
        # TODO in future - make pluggable based on file_type.format
        # (in this case CSV)
        # ONLY processing CSV files at the moment, so all the work done here.

        try:
            if attrs['file_type'].format.description == u'CSV file':
                # TODO possibly a file specific serializer instead of utility f?
                return validate_csv_file(attrs)
            else:
                return attrs
        except KeyError:
            raise serializers.ValidationError(
                {'file_type': 'File Type not found'}
            )
        except Exception, e:
            raise serializers.ValidationError('{0}'.format(e))
