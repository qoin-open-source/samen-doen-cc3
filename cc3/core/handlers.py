import logging

from django.core.files.uploadhandler import FileUploadHandler
from django.core.cache import cache


LOG = logging.getLogger(__name__)


# https://djangosnippets.org/snippets/678/
class UploadProgressCachedHandler(FileUploadHandler):
    """
    Tracks progress for file uploads.
    The http post request must contain a header or query parameter,
    'X-Progress-ID' which should contain a unique string to identify the
    upload to be tracked.
    """
    def __init__(self, request=None):
        super(UploadProgressCachedHandler, self).__init__(request)
        self.progress_id = None
        self.cache_key = None

    def handle_raw_input(self, input_data, META, content_length, boundary,
                         encoding=None):
        self.content_length = content_length
        if 'X-Progress-ID' in self.request.GET:
            self.progress_id = self.request.GET['X-Progress-ID']
        elif 'X-Progress-ID' in self.request.META:
            self.progress_id = self.request.META['X-Progress-ID']
        LOG.debug('UploadProgressCachedHandler: handle_raw_input() '
                  'self.progress_id {1}'.format(self.progress_id))
        if self.progress_id:
            self.cache_key = '{0}_{1}'.format(
                self.request.META['REMOTE_ADDR'], self.progress_id)
            LOG.debug('UploadProgressCachedHandler: handle_raw_input() '
                      'self.cache_key {0}'.format(self.cache_key))

            cache.set(self.cache_key, {
                'length': self.content_length,
                'uploaded': 0
            })

    def new_file(self, field_name, file_name, content_type, content_length,
                 charset=None):
        pass

    def receive_data_chunk(self, raw_data, start):
        if self.cache_key:
            LOG.debug('UploadProgressCachedHandler: receive_data_chunk() '
                      'self.cache_key {0}'.format(self.cache_key))

            data = cache.get(self.cache_key)
            data['uploaded'] += self.chunk_size
            LOG.debug("UploadProgressCachedHandler: receive_data_chunk() "
                      "data['uploaded'] {0}, self.chunk_size {1}".format(
                          data['uploaded'], self.chunk_size))
            cache.set(self.cache_key, data)
        return raw_data
    
    def file_complete(self, file_size):
        pass

    def upload_complete(self):
        if self.cache_key:
            cache.delete(self.cache_key)
