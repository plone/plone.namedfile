from plone.dexterity.content import Item
from plone.namedfile.field import NamedImage as NamedImageField
from plone.namedfile.file import NamedImage
from plone.namedfile.testing import PLONE_NAMEDFILE_INTEGRATION_TESTING
from plone.namedfile.tests import dummy
from unittest.mock import patch
from zope.component import queryMultiAdapter
from zope.publisher.browser import TestRequest

import plone.namedfile.adapters
import unittest


try:
    from plone.base.interfaces import IImageScalesFieldAdapter
except ImportError:
    IImageScalesFieldAdapter = None


def patch_get_scale_infos():
    # The IRegistry utility cannot be found in the test layer,
    # so we mock what Plone 6 would return.
    return [
        ("huge", 1600, 65536),
        ("great", 1200, 65536),
        ("larger", 1000, 65536),
        ("large", 800, 65536),
        ("teaser", 600, 65536),
        ("preview", 400, 65536),
        ("mini", 200, 65536),
        ("thumb", 128, 128),
        ("tile", 64, 64),
        ("icon", 32, 32),
        ("listing", 16, 16),
    ]


class ImageScalesAdaptersRegisteredTest(unittest.TestCase):
    """Test portal actions control panel."""

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def setUp(self):
        self.request = TestRequest()
        self.content = Item()

    @patch.object(
        plone.namedfile.adapters,
        "_get_scale_infos",
        new=patch_get_scale_infos,
        spec=True,
    )
    def serialize(self, context, field):
        serializer = queryMultiAdapter(
            (field, context, self.request), IImageScalesFieldAdapter
        )
        if serializer:
            return serializer()
        return

    def create_field(self, value=None):
        field = NamedImageField()
        field.__name__ = "image1"
        field.set(self.content, value)
        return field

    @unittest.skipIf(IImageScalesFieldAdapter is None, "Skipping on Plone 5")
    def test_field_adapter_return_scales(self):
        image = NamedImage(dummy.Image(), filename="dummy.gif")
        field = self.create_field(image)
        res = self.serialize(self.content, field)
        self.assertNotEqual(res, None)
        self.assertEqual(len(res), 1)
        res = res[0]
        download = res.pop("download")
        scales = res.pop("scales")
        self.assertEqual(
            res,
            {
                "content-type": "image/gif",
                "filename": "dummy.gif",
                "height": 16,
                "size": 168,
                "width": 16,
            },
        )
        # Note: self.content.absolute_url() is actually empty in this test.
        self.assertTrue(download.startswith("@@images/image1-16-"))
        self.assertTrue(download.endswith(".gif"))
        self.assertIn("listing", scales)
        self.assertEqual(len(scales), 1)
        listing = scales["listing"]
        self.assertEqual(sorted(listing.keys()), ["download", "height", "width"])
        self.assertEqual(listing["height"], 16)
        self.assertEqual(listing["width"], 16)
        download = listing["download"]
        self.assertTrue(download.startswith("@@images/image1-16-"))
        self.assertTrue(download.endswith(".gif"))

    @unittest.skipIf(IImageScalesFieldAdapter is not None, "Skipping on Plone 6")
    def test_field_adapter_return_nothing_without_plone_base(self):
        image = NamedImage(dummy.Image(), filename="dummy.gif")
        field = self.create_field(image)
        res = self.serialize(self.content, field)
        self.assertIsNone(res)

    def test_field_adapter_do_not_return_scales_for_empty_fields_with_adapter(self):
        field = self.create_field()
        res = self.serialize(self.content, field)
        self.assertEqual(res, None)

    @unittest.skipIf(IImageScalesFieldAdapter is None, "Skipping on Plone 5")
    def test_field_adapter_does_not_return_larger_scales(self):
        # Add an image of 900 by 900 pixels.
        image = NamedImage(dummy.JpegImage(), filename="900.jpeg")
        field = self.create_field(image)
        res = self.serialize(self.content, field)
        self.assertNotEqual(res, None)
        self.assertEqual(len(res), 1)
        res = res[0]
        download = res.pop("download")
        scales = res.pop("scales")
        self.assertEqual(
            res,
            {
                "content-type": "image/jpeg",
                "filename": "900.jpeg",
                "height": 900,
                "size": 160651,
                "width": 900,
            },
        )
        # Note: self.content.absolute_url() is actually empty in this test.
        self.assertTrue(download.startswith("@@images/image1-900-"))
        self.assertTrue(download.endswith(".jpeg"))
        # larger and huge should not be in here: these scales would return the same
        # content as the original.
        self.assertEqual(
            sorted(scales.keys()),
            ["icon", "large", "listing", "mini", "preview", "teaser", "thumb", "tile"],
        )
        preview = scales["preview"]
        self.assertEqual(preview["width"], 400)
        self.assertEqual(preview["height"], 400)
        self.assertTrue(preview["download"].startswith("@@images/image1-400-"))
