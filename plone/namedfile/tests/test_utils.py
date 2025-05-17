from plone.namedfile.file import NamedImage
from plone.namedfile.tests import getFile
from plone.namedfile.utils import get_contenttype
from plone.namedfile.utils import getImageInfo

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
                    filename="image.gif",
                )
            ),
            "image/gif",
        )
        self.assertEqual(
            get_contenttype(
                NamedImage(
                    getFile("image.tif"),
                    filename="image.tif",
                )
            ),
            "image/tiff",
        )
        self.assertEqual(
            get_contenttype(
                NamedImage(
                    getFile("notimage.doc"),
                    filename="notimage.doc",
                )
            ),
            "application/msword",
        )

        # Filename only detection of a non-IANA registered type.
        self.assertEqual(
            get_contenttype(filename="image.webp"),
            "image/webp",
        )

        # Filename only detection of a non-IANA registered type.
        self.assertEqual(
            get_contenttype(filename="song.midi"),
            "audio/midi",
        )

        # Detection of a surely not registered type.
        self.assertEqual(
            get_contenttype(filename="nothing.plonenamedfile"),
            "application/octet-stream",
        )

    def test_get_image_info(self):

        # WEBP WP8
        self.assertEqual(
            getImageInfo(getFile("image_lossy.webp")),
            ("image/webp", 500, 200),
        )

        # WEBP WP8L
        self.assertEqual(
            getImageInfo(getFile("image_loseless.webp")),
            ("image/webp", 200, 200),
        )

        # PNG
        self.assertEqual(
            getImageInfo(getFile("image.png")),
            ("image/png", 200, 200),
        )

        # BMP3
        self.assertEqual(
            getImageInfo(getFile("image.bmp")),
            ("image/x-ms-bmp", 200, 200),
        )
