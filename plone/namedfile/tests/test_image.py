# This file is partially borrowed from zope.app.file and licensed ZPL.

from DateTime import DateTime
from plone.namedfile.file import NamedImage
from plone.namedfile.interfaces import INamedImage
from plone.namedfile.tests import MockNamedImage
from zope.interface.verify import verifyClass

import time
import unittest


zptlogo = (
    b"GIF89a\x10\x00\x10\x00\xd5\x00\x00\xff\xff\xff\xff\xff\xfe\xfc\xfd\xfd"
    b"\xfa\xfb\xfc\xf7\xf9\xfa\xf5\xf8\xf9\xf3\xf6\xf8\xf2\xf5\xf7\xf0\xf4\xf6"
    b"\xeb\xf1\xf3\xe5\xed\xef\xde\xe8\xeb\xdc\xe6\xea\xd9\xe4\xe8\xd7\xe2\xe6"
    b"\xd2\xdf\xe3\xd0\xdd\xe3\xcd\xdc\xe1\xcb\xda\xdf\xc9\xd9\xdf\xc8\xd8\xdd"
    b"\xc6\xd7\xdc\xc4\xd6\xdc\xc3\xd4\xda\xc2\xd3\xd9\xc1\xd3\xd9\xc0\xd2\xd9"
    b"\xbd\xd1\xd8\xbd\xd0\xd7\xbc\xcf\xd7\xbb\xcf\xd6\xbb\xce\xd5\xb9\xcd\xd4"
    b"\xb6\xcc\xd4\xb6\xcb\xd3\xb5\xcb\xd2\xb4\xca\xd1\xb2\xc8\xd0\xb1\xc7\xd0"
    b"\xb0\xc7\xcf\xaf\xc6\xce\xae\xc4\xce\xad\xc4\xcd\xab\xc3\xcc\xa9\xc2\xcb"
    b"\xa8\xc1\xca\xa6\xc0\xc9\xa4\xbe\xc8\xa2\xbd\xc7\xa0\xbb\xc5\x9e\xba\xc4"
    b"\x9b\xbf\xcc\x98\xb6\xc1\x8d\xae\xbaFgs\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00,\x00\x00\x00\x00\x10\x00\x10\x00\x00\x06z@\x80pH,\x12k\xc8$\xd2f\x04"
    b"\xd4\x84\x01\x01\xe1\xf0d\x16\x9f\x80A\x01\x91\xc0ZmL\xb0\xcd\x00V\xd4"
    b"\xc4a\x87z\xed\xb0-\x1a\xb3\xb8\x95\xbdf8\x1e\x11\xca,MoC$\x15\x18{"
    b"\x006}m\x13\x16\x1a\x1f\x83\x85}6\x17\x1b $\x83\x00\x86\x19\x1d!%)\x8c"
    b"\x866#'+.\x8ca`\x1c`(,/1\x94B5\x19\x1e\"&*-024\xacNq\xba\xbb\xb8h\xbeb"
    b"\x00A\x00;"
)


class TestImage(unittest.TestCase):
    def _makeImage(self, *args, **kw):
        return NamedImage(*args, **kw)

    def testEmpty(self):
        file_img = self._makeImage()
        self.assertEqual(file_img.contentType, "")
        self.assertEqual(bytes(file_img.data), b"")
        self.assertIsNotNone(file_img.modified)

    def testConstructor(self):
        file_img = self._makeImage(b"Data")
        self.assertEqual(file_img.contentType, "")
        self.assertEqual(bytes(file_img.data), b"Data")
        self.assertIsNotNone(file_img.modified)

    def testMutators(self):
        image = self._makeImage()
        image.contentType = "image/jpeg"
        self.assertEqual(image.contentType, "image/jpeg")

        image._setData(zptlogo)
        self.assertEqual(image.data, zptlogo)
        self.assertEqual(image.contentType, "image/gif")
        self.assertEqual(image.getImageSize(), (16, 16))

    def testModifiedTimeStamp(self):
        image = self._makeImage()
        old_timestamp = image.modified
        time.sleep(1 / 1000)  # make sure at least 1ms passes
        image._setData(zptlogo)
        self.assertNotEqual(image.modified, old_timestamp)

    def testFallBackToDatabaseModifiedTimeStamp(self):
        dt = DateTime()
        image = MockNamedImage()
        image._p_mtime = dt.millis()
        image._modified = (dt + 1).millis()

        delattr(image, "_modified")
        marker = object()
        self.assertEqual(marker, getattr(image, "_modified", marker))
        self.assertEqual(dt.millis(), image._p_mtime)

    def testInterface(self):
        self.assertTrue(INamedImage.implementedBy(NamedImage))
        self.assertTrue(verifyClass(INamedImage, NamedImage))

    def test_extract_media_type(self):
        from plone.namedfile.utils import extract_media_type as extract

        self.assertIsNone(extract(None))
        self.assertEqual(extract("text/plain"), "text/plain")
        self.assertEqual(extract("TEXT/PLAIN"), "text/plain")
        self.assertEqual(extract("text / plain"), "text/plain")
        self.assertEqual(extract(" text/plain ; charset=utf-8"), "text/plain")
