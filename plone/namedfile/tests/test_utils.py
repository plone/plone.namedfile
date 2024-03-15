from plone.namedfile.file import NamedImage
from plone.namedfile.tests import getFile
from plone.namedfile.utils import get_contenttype

import unittest


class TestUtils(unittest.TestCase):

    def test_get_contenttype(self):
        self.assertEqual(
            get_contenttype(
                NamedImage(
                    getFile("image.gif"),
                    contentType="image/gif",
                )
            ),
            "image/gif",
        )
        self.assertEqual(
            get_contenttype(
                NamedImage(
                    getFile("image.gif"),
                    filename=u"image.gif",
                )
            ),
            "image/gif",
        )
        self.assertEqual(
            get_contenttype(
                NamedImage(
                    getFile("image.tif"),
                    filename=u"image.tif",
                )
            ),
            "image/tiff",
        )
        self.assertEqual(
            get_contenttype(
                NamedImage(
                    getFile("notimage.doc"),
                    filename=u"notimage.doc",
                )
            ),
            "application/msword",
        )

        # Filename only detection of a non-IANA registered type.
        self.assertEqual(
            get_contenttype(filename=u"image.webp"),
            "image/webp",
        )

        # Filename only detection of a non-IANA registered type.
        self.assertEqual(
            get_contenttype(filename=u"song.midi"),
            "audio/midi",
        )

        # Detection of a surely not registered type.
        self.assertEqual(
            get_contenttype(filename=u"nothing.plonenamedfile"),
            "application/octet-stream",
        )
