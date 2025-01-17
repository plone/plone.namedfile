from DateTime import DateTime
from io import BytesIO
from OFS.SimpleItem import SimpleItem
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.namedfile.field import NamedImage as NamedImageField
from plone.namedfile.file import NamedImage
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.namedfile.scaling import ImageScaling
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.tests import getFile
from plone.testing.zope import Browser
from zExceptions import BadRequest
from zope.annotation import IAttributeAnnotatable
from zope.interface import implementer

import PIL
import transaction
import unittest


class IHasImage(IImageScaleTraversable):
    image = NamedImageField()


def assertImage(testcase, data, format_, size):
    image = PIL.Image.open(BytesIO(data))
    testcase.assertEqual(image.format, format_)
    testcase.assertEqual(image.size, size)


@implementer(IAttributeAnnotatable, IHasImage)
class DummyContent(SimpleItem):
    image = None
    modified = DateTime
    id = __name__ = "item"
    title = "foo"

    def Title(self):
        return self.title


class ImagePublisherTests(unittest.TestCase):

    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def setUp(self):
        data = getFile("image.png")
        item = DummyContent()
        item.image = NamedImage(data, "image/png", "image.png")
        self.layer["app"]._setOb("item", item)
        self.item = self.layer["app"].item
        self.view = self.item.unrestrictedTraverse("@@images")
        self._orig_sizes = ImageScaling._sizes

        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader("Referer", self.layer["app"].absolute_url())

    def tearDown(self):
        ImageScaling._sizes = self._orig_sizes

    def testPublishScaleViaUID(self):
        scale = self.view.scale("image", width=64, height=64)
        transaction.commit()
        # make sure the referenced image scale is available
        self.browser.open(scale.url)
        self.assertEqual("image/png", self.browser.headers["content-type"])
        assertImage(self, self.browser.contents, "PNG", (64, 64))

    def testPublishWebDavScaleViaUID(self):
        scale = self.view.scale("image", width=64, height=64)
        transaction.commit()
        # make sure the referenced image scale is available
        self.browser.open(scale.url + "/manage_DAVget")
        self.assertEqual("image/png", self.browser.headers["content-type"])
        assertImage(self, self.browser.contents, "PNG", (64, 64))

    def testPublishFTPScaleViaUID(self):
        scale = self.view.scale("image", width=64, height=64)
        transaction.commit()
        # make sure the referenced image scale is available
        self.browser.open(scale.url + "/manage_FTPget")
        self.assertIn("200", self.browser.headers["status"])
        # Same remark as in testPublishWebDavScaleViaUID is valid here.
        self.assertEqual("image/png", self.browser.headers["content-type"])
        assertImage(self, self.browser.contents, "PNG", (64, 64))

    def testHeadRequestMethod(self):
        scale = self.view.scale("image", width=64, height=64)
        transaction.commit()
        # make sure the referenced image scale is available
        url = str(scale.url)
        self.browser.open(url)
        GET_length = len(self.browser.contents)

        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader("Referer", self.layer["app"].absolute_url())

        def make_head_request(args):
            return self.browser.testapp.head(url, **args)

        self.browser._processRequest(url, make_head_request)

        self.assertEqual("image/png", self.browser.headers["content-type"])
        self.assertEqual(self.browser.headers["Content-Length"], str(GET_length))
        self.assertEqual(self.browser.contents, b"")

    def testPublishThumbViaUID(self):
        ImageScaling._sizes = {"thumb": (128, 128)}
        scale = self.view.scale("image", "thumb")
        transaction.commit()
        # make sure the referenced image scale is available
        self.browser.open(scale.url)
        self.assertEqual("image/png", self.browser.headers["content-type"])
        assertImage(self, self.browser.contents, "PNG", (128, 128))

    def testPublishCustomSizeViaUID(self):
        # set custom image sizes
        ImageScaling._sizes = {"foo": (23, 23)}
        scale = self.view.scale("image", "foo")
        transaction.commit()
        # make sure the referenced image scale is available
        self.browser.open(scale.url)
        self.assertEqual("image/png", self.browser.headers["content-type"])
        assertImage(self, self.browser.contents, "PNG", (23, 23))

    def testPublishThumbViaName(self):
        ImageScaling._sizes = {"thumb": (128, 128)}
        transaction.commit()

        # make sure traversing works as is and with scaling
        # first the field without a scale name
        self.browser.open(self.layer["app"].absolute_url() + "/item/@@images/image")
        self.assertEqual("image/png", self.browser.headers["content-type"])
        self.assertEqual(self.browser.contents, getFile("image.png"))

        # and last a scaled version
        self.browser.open(
            self.layer["app"].absolute_url() + "/item/@@images/image/thumb"
        )
        self.assertEqual("image/png", self.browser.headers["content-type"])
        assertImage(self, self.browser.contents, "PNG", (128, 128))

    def testPublishCustomSizeViaName(self):
        # set custom image sizes
        ImageScaling._sizes = {"foo": (23, 23)}
        transaction.commit()
        # make sure traversing works as expected
        self.browser.open(self.layer["app"].absolute_url() + "/item/@@images/image/foo")
        assertImage(self, self.browser.contents, "PNG", (23, 23))

    def testPublishScaleWithInvalidUID(self):
        scale = self.view.scale("image", width=64, height=64)
        transaction.commit()
        # change the url so it's invalid...
        from zExceptions import NotFound

        with self.assertRaises(NotFound):
            self.browser.open(scale.url.replace(".png", "x.png"))

    def testPublishScaleWithInvalidScale(self):
        scale = self.view.scale("image", "no-such-scale")
        transaction.commit()
        self.assertEqual(scale, None)

    def test_getAvailableSizesWithInvalidScaleMethod(self):
        self.assertEqual(self.view.getAvailableSizes("no-such-scale"), {})

    def test_getAvailableSizesWithInvalidScaleProperty(self):
        self.assertEqual(self.view.available_sizes, {})

    def test_getImageSizeWithInvalidScale(self):
        self.assertEqual(self.view.getImageSize("no-such-scale"), (0, 0))

    def testGuardedAccess(self):
        # make sure it's not possible to access scales of forbidden images
        self.item.__allow_access_to_unprotected_subobjects__ = 0
        ImageScaling._sizes = {"foo": (23, 23)}
        transaction.commit()
        self.browser.addHeader(
            "Authorization",
            f"Basic {TEST_USER_NAME:s}:{TEST_USER_PASSWORD:s}",
        )
        from zExceptions import Unauthorized

        with self.assertRaises(Unauthorized):
            self.browser.open(
                self.layer["app"].absolute_url() + "/item/@@images/image/foo"
            )
        self.item.__allow_access_to_unprotected_subobjects__ = 1

    def testSVGPublishThumbViaName(self):
        ImageScaling._sizes = {"thumb": (128, 128)}

        data = getFile("image.svg")
        svg = DummyContent()
        svg.image = NamedImage(data, "image/svg+xml", "image.svg")
        self.layer["app"]._setOb("svg", svg)
        svg = self.layer["app"].svg

        transaction.commit()

        # make sure traversing works as is and with scaling
        # first the field without a scale name
        self.browser.open(self.layer["app"].absolute_url() + "/svg/@@images/image")

        self.assertEqual("image/svg+xml", self.browser.headers["content-type"])
        self.assertEqual(self.browser.contents, getFile("image.svg"))

        # and last a scaled version
        self.browser.open(
            self.layer["app"].absolute_url() + "/svg/@@images/image/thumb"
        )
        self.assertEqual("image/svg+xml", self.browser.headers["content-type"])
        self.assertEqual(self.browser.contents, data)

    def testImagesViewWithNoSubpath(self):
        transaction.commit()
        with self.assertRaises(BadRequest):
            self.browser.open(self.layer["app"].absolute_url() + "/item/@@images")


def test_suite():
    from unittest import defaultTestLoader

    return defaultTestLoader.loadTestsFromName(__name__)
