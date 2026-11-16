from OFS.SimpleItem import SimpleItem
from plone.namedfile import field
from plone.namedfile import file
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.tests import getFile
from plone.testing.zope import Browser
from unittest import mock
from ZODB.blob import Blob
from zope.interface import implementer
from zope.interface import Interface

import transaction
import unittest


class ISchema(Interface):
    blob_file = field.NamedBlobFile()


@implementer(ISchema)
class DummyContent(SimpleItem):
    blob_file = None
    id = __name__ = "item"
    title = "foo"

    def Title(self):
        return self.title


class TestDownloadHeadRequest(unittest.TestCase):
    """HEAD on @@download and @@display-file sends the headers only.

    Neither ZPublisher nor waitress drop the body of a HEAD response.
    Streaming the blob to a client that never reads it blocks a worker
    thread until the connection is closed.
    """

    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def setUp(self):
        item = DummyContent()
        item.blob_file = file.NamedBlobFile(getFile("file.pdf"), filename="file.pdf")
        self.layer["app"]._setOb("item", item)
        self.item = self.layer["app"].item
        transaction.commit()
        self.data = getFile("file.pdf")

    def tearDown(self):
        self.layer["app"]._delOb("item")
        transaction.commit()

    def browser(self):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        return browser

    def head(self, url):
        browser = self.browser()
        browser._processRequest(url, lambda args: browser.testapp.head(url, **args))
        return browser

    def watch_blob_stream(self):
        # stream_data opens committed blobs with Blob.committed()
        return mock.patch.object(
            Blob, "committed", autospec=True, side_effect=Blob.committed
        )

    def test_head_download(self):
        url = self.item.absolute_url() + "/@@download/blob_file"
        with self.watch_blob_stream() as committed:
            browser = self.head(url)

        self.assertEqual(browser.headers["Content-Length"], str(len(self.data)))
        self.assertEqual(browser.headers["Content-Type"], "application/pdf")
        self.assertIn("attachment", browser.headers["Content-Disposition"])
        self.assertEqual(browser.contents, b"")
        committed.assert_not_called()

    def test_head_display_file(self):
        url = self.item.absolute_url() + "/@@display-file/blob_file"
        with self.watch_blob_stream() as committed:
            browser = self.head(url)

        self.assertEqual(browser.headers["Content-Length"], str(len(self.data)))
        self.assertEqual(browser.headers["Content-Type"], "application/pdf")
        self.assertIn("inline", browser.headers["Content-Disposition"])
        self.assertEqual(browser.contents, b"")
        committed.assert_not_called()

    def test_head_download_ignores_range(self):
        # Range is only defined for GET (RFC 9110, section 14.2)
        url = self.item.absolute_url() + "/@@download/blob_file"
        browser = self.browser()
        browser.addHeader("Range", "bytes=0-9")
        browser._processRequest(url, lambda args: browser.testapp.head(url, **args))

        self.assertEqual(browser.headers["Content-Length"], str(len(self.data)))
        self.assertNotIn("Content-Range", browser.headers)
        self.assertEqual(browser.contents, b"")

    def test_get_download_unchanged(self):
        url = self.item.absolute_url() + "/@@download/blob_file"
        with self.watch_blob_stream() as committed:
            browser = self.browser()
            browser.open(url)

        self.assertEqual(browser.headers["Content-Length"], str(len(self.data)))
        self.assertEqual(browser.contents, self.data)
        # the check in the HEAD tests is not vacuous
        committed.assert_called()

    def test_get_download_range_unchanged(self):
        url = self.item.absolute_url() + "/@@download/blob_file"
        browser = self.browser()
        browser.addHeader("Range", "bytes=0-9")
        browser.open(url)

        self.assertEqual(browser.headers["Status"], "206 Partial Content")
        self.assertEqual(
            browser.headers["Content-Range"], f"bytes 0-9/{len(self.data)}"
        )
        self.assertEqual(browser.contents, self.data[:10])
