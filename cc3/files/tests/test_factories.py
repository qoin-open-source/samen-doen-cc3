import logging

import factory

from cc3.cyclos.tests.test_factories import UserFactory

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class FormatFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'files.Format'


class FileTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'files.FileType'

    format = factory.SubFactory(FormatFactory)


class UploadFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'files.Upload'


class FileServiceUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'files.FileServiceUser'

    user = factory.SubFactory(UserFactory)
