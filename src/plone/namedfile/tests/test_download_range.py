"""Range requests on @@download, published the way waitress does it.

Zope hands the range iterator to ``wsgi.file_wrapper`` because it has a ``read``
method. waitress then reads the wrapper in blocks instead of iterating it. The
server cuts the response at Content-Length, so the client gets the right bytes
either way, but the iterator must stop at the end of the range by itself.
"""

from OFS.SimpleItem import SimpleItem
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from waitress.buffers import ReadOnlyFileBasedBuffer
from ZPublisher.WSGIPublisher import publish_module

import io
import sys
import transaction
import unittest


class DummyContent(SimpleItem):
    id = __name__ = "item"
    file = None


class TestDownloadRange(unittest.TestCase):
    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def setUp(self):
        app = self.layer["app"]
        app._setOb("item", DummyContent())
        # 256 KiB, more than the 32 KiB blocks waitress reads
        self.data = bytes(range(256)) * 1024
        app.item.file = NamedBlobFile(self.data, filename="data.bin")
        # the iterator is only used for committed blobs
        transaction.commit()

    def publish(self, **headers):
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/item/@@download/file",
            "SERVER_NAME": "nohost",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(),
            "wsgi.errors": sys.stderr,
            "wsgi.file_wrapper": ReadOnlyFileBasedBuffer,
        }
        environ.update(headers)
        response = {}

        def start_response(status, response_headers, exc_info=None):
            response["status"] = status
            response["headers"] = {
                key.lower(): value for key, value in response_headers
            }

        result = publish_module(environ, start_response)
        try:
            # everything the file wrapper reads, not cut at Content-Length
            body = b"".join(result)
        finally:
            result.close()
        return response["status"], response["headers"], body

    def test_range_request_reads_only_the_range(self):
        start, end = 65536, 131072
        status, headers, body = self.publish(HTTP_RANGE=f"bytes={start}-{end - 1}")
        self.assertEqual(status, "206 Partial Content")
        self.assertEqual(headers["content-length"], str(end - start))
        self.assertEqual(
            headers["content-range"], f"bytes {start}-{end - 1}/{len(self.data)}"
        )
        self.assertEqual(body, self.data[start:end])

    def test_request_without_range_reads_the_whole_file(self):
        status, headers, body = self.publish()
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["content-length"], str(len(self.data)))
        self.assertEqual(body, self.data)
