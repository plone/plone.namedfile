from DateTime import DateTime
from doctest import _ellipsis_match
from io import BytesIO
from OFS.SimpleItem import SimpleItem
from plone.namedfile.field import NamedImage as NamedImageField
from plone.namedfile.file import NamedImage
from plone.namedfile.interfaces import IAvailableSizes
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.namedfile.scaling import ImageScale
from plone.namedfile.scaling import ImageScaling
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.testing import PLONE_NAMEDFILE_INTEGRATION_TESTING
from plone.namedfile.tests import getFile
from plone.namedfile.tests import MockNamedImage
from plone.rfc822.interfaces import IPrimaryFieldInfo
from plone.scale.interfaces import IScaledImageQuality
from plone.scale.storage import IImageScaleStorage
from unittest.mock import patch
from zExceptions import Unauthorized
from zope.annotation import IAttributeAnnotatable
from zope.component import adapter
from zope.component import getGlobalSiteManager
from zope.component import getSiteManager
from zope.interface import implementer
from zope.interface import Interface
from zope.publisher.interfaces import NotFound

import PIL
import plone.namedfile.picture
import plone.namedfile.scaling
import re
import time
import unittest
import warnings


# Unique scale name used to be a uuid.uui4(),
# which is a combination of hexadecimal digits with dashes, total 36.
# Now it is 'imagescalename-width-hash', where hash is 32.
PAT_UID_SCALE = r"[0-9a-z]*-[0-9]*-[0-9a-f]{32}"


def wait_to_ensure_modified():
    # modified is measured in milliseconds
    # wait 5ms to ensure modified will have changed
    time.sleep(0.005)


class IHasImage(IImageScaleTraversable):
    image = NamedImageField()


def assertImage(testcase, data, format_, size):
    image = PIL.Image.open(BytesIO(data))
    testcase.assertEqual(image.format, format_)
    testcase.assertEqual(image.size, size)


def patch_Img2PictureTag_picture_variants():

    return {
        "large": {
            "title": "Large",
            "sourceset": [
                {
                    "scale": "larger",
                    "additionalScales": [
                        "preview",
                        "teaser",
                        "large",
                        "great",
                        "huge",
                    ],
                }
            ],
        },
        "medium": {
            "title": "Medium",
            "sourceset": [
                {
                    "scale": "teaser",
                    "additionalScales": ["preview", "large", "larger", "great"],
                }
            ],
        },
        "small": {
            "title": "Small",
            "sourceset": [
                {
                    "scale": "preview",
                    "additionalScales": ["preview", "large", "larger"],
                }
            ],
        },
    }


def patch_Img2PictureTag_empty_picture_variants():
    # You would have this in Plone 5.2, or if someone empties the registry setting.
    return {}


def patch_Img2PictureTag_allowed_scales():

    return {
        "huge": (1600, 65536),
        "great": (1200, 65536),
        "larger": (1000, 65536),
        "large": (800, 65536),
        "teaser": (600, 65536),
        "preview": (400, 65536),
        "mini": (200, 65536),
        "thumb": (128, 128),
        "tile": (64, 64),
        "icon": (32, 32),
        "listing": (16, 16),
    }


@implementer(IAttributeAnnotatable, IHasImage)
class DummyContent(SimpleItem):
    image = None
    modified = DateTime
    id = __name__ = "item"
    title = "foo"

    def Title(self):
        return self.title

    def UID(self):
        return "dummy_uuid"


@implementer(IPrimaryFieldInfo)
@adapter(DummyContent)
class PrimaryFieldInfo:
    def __init__(self, context):
        self.context = context
        self.fieldname = "image"
        self.field = self.context.image

    @property
    def value(self):
        return self.field


@implementer(IScaledImageQuality)
class DummyQualitySupplier:
    """fake utility for image quality setting from imaging control panel."""

    def getQuality(self):
        return 1  # as bad as it gets


class FakeImage:
    def __init__(self, value, format, key=None, uid="image"):
        self.value = value
        self.format = format
        self._width = len(value)
        self._height = len(format)
        self.contentType = f"image/{format}"
        # variables for scales:
        self._scales = {}
        self.key = key
        self.uid = uid

    @property
    def data(self):
        return self

    @property
    def info(self):
        return dict(
            data=self.data,
            width=self._width,
            height=self._height,
            mimetype=f"image/{self.format.lower()}",
            key=self.key,
            uid=self.uid,
        )

    def absolute_url(self):
        return "http://fake.image"

    def Title(self):
        # used for tag
        return "Image Title"


@implementer(IImageScaleStorage)
class FakeImageScaleStorage:
    """Storage class for FakeImages."""

    def __init__(self, context, modified=None):
        """Adapt the given context item and optionally provide a callable
        to return a representation of the last modification date, which
        can be used to invalidate stored scale data on update."""
        self.context = context
        self.modified = modified
        self.storage = context._scales

    def pre_scale(self, factory=None, **parameters):
        """Find image scale data for the given parameters or pre-create it.

        In our version, we only support height and width.
        """
        stripped_parameters = {
            "target_height": parameters.get("height"),
            "target_width": parameters.get("width"),
        }
        key = self.hash(**stripped_parameters)
        info = self.get_info_by_hash(key)
        if info is not None:
            # Note: we could do something with self.modified here,
            # but we choose to ignore it.
            return info
        return self.create_scale(no_scale=True, **stripped_parameters)

    def scale(self, factory=None, **parameters):
        """Find image scale data for the given parameters or create it.

        In our version, we only support height and width.
        """
        stripped_parameters = {
            "target_height": parameters.get("height"),
            "target_width": parameters.get("width"),
        }
        key = self.hash(**stripped_parameters)
        info = self.get_info_by_hash(key)
        if info is not None:
            # Note: we could do something with self.modified here,
            # but we choose to ignore it.
            return info
        return self.create_scale(**stripped_parameters)

    def create_scale(self, target_height=None, target_width=None, no_scale=False):
        if target_height is None and target_width is None:
            # Return the original.
            return self.context.info

        # We have a funny way of scaling.
        value = self.context.value[:target_height]
        format = self.context.format[:target_width]

        # Get uid and key.
        # Our implementation never throws away scales, so we can use uid-0, uid-1, etc.
        # Note: in ImageScaling.publishTraverse a dash in the url means it is a scale uid.
        uid = f"uid-{len(self.storage)}"
        key = self.hash(target_height=target_height, target_width=target_width)

        if no_scale:
            info = dict(
                data=None,
                width=self._width,
                height=self._height,
                mimetype=f"image/{self.format.lower()}",
                key=self.key,
                uid=self.uid,
            )
        else:
            # Create a new fake image for this scale.
            scale = FakeImage(value, format, key=key, uid=uid)
            info = scale.info

        # Store the real scale or placeholder scale and return the info.
        self.storage[uid] = info
        return scale.info

    def __getitem__(self, uid):
        """Find image scale data based on its uid."""
        return self.storage[uid]

    def get(self, uid, default=None):
        return self.storage.get(uid, default)

    def get_or_generate(self, uid, default=None):
        info = self.storage.get(uid, default)
        if info is None:
            return
        if info.get("data"):
            return info
        # We have a placeholder. Get real data.
        stripped_parameters = {
            "target_height": info.get("height"),
            "target_width": info.get("width"),
        }
        return self.create_scale(**stripped_parameters)

    def hash(self, **parameters):
        return tuple(parameters.values())

    def get_info_by_hash(self, hash):
        for value in self.storage.values():
            if value["key"] == hash:
                return value


class TitleImageScale(ImageScale):
    """ImageScale class with its own title property."""

    title = "title from class"


# @patch.multiple(
#     "plone.namedfile.scaling.Img2PictureTag",
#     allowed_scales=patch_Img2PictureTag_allowed_scales,
#     picture_variants=patch_Img2PictureTag_picture_variants,
#     spec=True,
# )
class ImageScalingTests(unittest.TestCase):

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def setUp(self):
        sm = getSiteManager()
        sm.registerAdapter(PrimaryFieldInfo)

        data = getFile("image.png")
        item = DummyContent()
        item.image = MockNamedImage(data, "image/png", "image.png")
        self.layer["app"]._setOb("item", item)
        self.item = self.layer["app"].item
        self._orig_sizes = ImageScaling._sizes
        self.scaling = ImageScaling(self.item, None)

    def tearDown(self):
        ImageScaling._sizes = self._orig_sizes
        sm = getSiteManager()
        sm.unregisterAdapter(PrimaryFieldInfo)

    def testCreateScale(self):
        foo = self.scaling.scale("image", width=100, height=80)
        self.assertTrue(foo.uid)
        self.assertEqual(foo.mimetype, "image/png")
        self.assertIsInstance(foo.mimetype, str)
        self.assertEqual(foo.data.contentType, "image/png")
        self.assertIsInstance(foo.data.contentType, str)
        self.assertEqual(foo.width, 80)
        self.assertEqual(foo.height, 80)
        assertImage(self, foo.data.data, "PNG", (80, 80))

    def testCreateExactScale(self):
        foo = self.scaling.scale("image", width=100, height=80)
        self.assertIsNot(foo.data, self.item.image)

        # test that exact scale without parameters returns original
        foo = self.scaling.scale(
            "image", width=self.item.image._width, height=self.item.image._height
        )
        self.assertIs(foo.data, self.item.image)

        foo = self.scaling.scale(
            "image",
            width=self.item.image._width,
            height=self.item.image._height,
            quality=80,
        )
        self.assertIsNot(foo.data, self.item.image)

    def testCreateHighPixelDensityScale(self):
        self.scaling.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        foo = self.scaling.scale("image", width=100, height=80, include_srcset=True)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]["mimetype"], "image/png")
        self.assertEqual(foo.srcset[0]["height"], 160)
        self.assertEqual(foo.srcset[0]["width"], 160)
        # It is a pre-registered scale, not yet rendered.
        self.assertEqual(foo.srcset[0]["data"], None)
        # Render the scale by pretending to visit its url.
        bar = self.scaling.publishTraverse(self.layer["request"], foo.srcset[0]["uid"])
        assertImage(self, bar.data.data, "PNG", (160, 160))

    def testCreateScaleWithoutData(self):
        item = DummyContent()
        scaling = ImageScaling(item, None)
        foo = scaling.scale("image", width=100, height=80)
        self.assertEqual(foo, None)

    def testCreateHighPixelDensityScaleWithoutData(self):
        item = DummyContent()
        scaling = ImageScaling(item, None)
        scaling.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        foo = scaling.scale("image", width=100, height=80)
        self.assertFalse(hasattr(foo, "srcset"))

    def testGetScaleByName(self):
        self.scaling.available_sizes = {"foo": (60, 60)}
        foo = self.scaling.scale("image", scale="foo")
        self.assertTrue(foo.uid)
        self.assertEqual(foo.mimetype, "image/png")
        self.assertIsInstance(foo.mimetype, str)
        self.assertEqual(foo.data.contentType, "image/png")
        self.assertIsInstance(foo.data.contentType, str)
        self.assertEqual(foo.width, 60)
        self.assertEqual(foo.height, 60)
        assertImage(self, foo.data.data, "PNG", (60, 60))
        expected_url = re.compile(rf"http://nohost/item/@@images/{PAT_UID_SCALE}.png")
        self.assertTrue(expected_url.match(foo.absolute_url()))
        self.assertEqual(foo.url, foo.absolute_url())

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            r'<img src="{}/@@images/({}).(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" />'.format(
                base, PAT_UID_SCALE
            )
        )
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetHighPixelDensityScaleByName(self):
        self.scaling.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        self.scaling.available_sizes = {"foo": (60, 60)}
        foo = self.scaling.scale("image", scale="foo", include_srcset=True)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]["mimetype"], "image/png")
        self.assertEqual(foo.srcset[0]["width"], 120)
        self.assertEqual(foo.srcset[0]["height"], 120)

        # It is a pre-registered scale, not yet rendered.
        self.assertEqual(foo.srcset[0]["data"], None)
        # Render the scale by pretending to visit its url.
        bar = self.scaling.publishTraverse(self.layer["request"], foo.srcset[0]["uid"])
        assertImage(self, bar.data.data, "PNG", (120, 120))

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            rf'<img src="{base}'
            + rf"/@@images/({PAT_UID_SCALE})"
            + r'.(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" '
            r'srcset="http://nohost/item/@@images/({})'.format(PAT_UID_SCALE)
            + r".(jpeg|gif|png)"
            r' 2x" />'
        )
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetRetinaScaleByWidthAndHeight(self):
        self.scaling.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        foo = self.scaling.scale("image", width=60, height=60, include_srcset=True)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]["mimetype"], "image/png")
        self.assertEqual(foo.srcset[0]["width"], 120)
        self.assertEqual(foo.srcset[0]["height"], 120)

        # It is a pre-registered scale, not yet rendered.
        self.assertEqual(foo.srcset[0]["data"], None)
        # Render the scale by pretending to visit its url.
        bar = self.scaling.publishTraverse(self.layer["request"], foo.srcset[0]["uid"])
        assertImage(self, bar.data.data, "PNG", (120, 120))

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            rf'<img src="{base}'
            + rf"/@@images/({PAT_UID_SCALE})"
            + r'.(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" '
            r'srcset="http://nohost/item/@@images/({})'.format(PAT_UID_SCALE)
            + r".(jpeg|gif|png)"
            r' 2x" />'
        )
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetRetinaScaleByWidthOnly(self):
        self.scaling.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        foo = self.scaling.scale("image", width=60, include_srcset=True)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]["mimetype"], "image/png")
        self.assertEqual(foo.srcset[0]["width"], 120)
        self.assertEqual(foo.srcset[0]["height"], 120)
        # It is a pre-registered scale, not yet rendered.
        self.assertEqual(foo.srcset[0]["data"], None)
        # Render the scale by pretending to visit its url.
        bar = self.scaling.publishTraverse(self.layer["request"], foo.srcset[0]["uid"])
        assertImage(self, bar.data.data, "PNG", (120, 120))

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            rf'<img src="{base}'
            + rf"/@@images/({PAT_UID_SCALE})"
            + r'.(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" '
            r'srcset="http://nohost/item/@@images/({})'.format(PAT_UID_SCALE)
            + r".(jpeg|gif|png)"
            r' 2x" />'
        )
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetRetinaScaleByHeightOnly(self):
        self.scaling.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        foo = self.scaling.scale("image", height=60, include_srcset=True)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]["mimetype"], "image/png")
        self.assertEqual(foo.srcset[0]["width"], 120)
        self.assertEqual(foo.srcset[0]["height"], 120)
        # It is a pre-registered scale, not yet rendered.
        self.assertEqual(foo.srcset[0]["data"], None)
        # Render the scale by pretending to visit its url.
        bar = self.scaling.publishTraverse(self.layer["request"], foo.srcset[0]["uid"])
        assertImage(self, bar.data.data, "PNG", (120, 120))

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            rf'<img src="{base}'
            + rf"/@@images/({PAT_UID_SCALE})"
            + r'.(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" '
            r'srcset="http://nohost/item/@@images/({})'.format(PAT_UID_SCALE)
            + r".(jpeg|gif|png)"
            r' 2x" />'
        )
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    @patch.object(
        plone.namedfile.scaling,
        "get_picture_variants",
        new=patch_Img2PictureTag_picture_variants,
        spec=True,
    )
    @patch.object(
        plone.namedfile.picture,
        "get_allowed_scales",
        new=patch_Img2PictureTag_allowed_scales,
        spec=True,
    )
    @patch.object(plone.namedfile.picture, "uuidToObject", spec=True)
    def testGetPictureTagByName(self, mock_uuid_to_object):
        ImageScaling._sizes = patch_Img2PictureTag_allowed_scales()
        mock_uuid_to_object.return_value = self.item
        tag = self.scaling.picture("image", picture_variant="medium")
        expected = """<picture>
 <source srcset="http://nohost/item/@@images/image-600-....png 600w,
http://nohost/item/@@images/image-400-....png 400w,
http://nohost/item/@@images/image-800-....png 800w,
http://nohost/item/@@images/image-1000-....png 1000w,
http://nohost/item/@@images/image-1200-....png 1200w"/>
 <img...src="http://nohost/item/@@images/image-600-....png".../>
</picture>"""
        self.assertTrue(_ellipsis_match(expected, tag.strip()))

        # The exact placement of the img tag attributes can differ, especially
        # with different beautifulsoup versions.
        # So check here that all attributes are present.
        self.assertIn('height="200"', tag)
        self.assertIn('loading="lazy"', tag)
        self.assertIn('title="foo"', tag)
        self.assertIn('width="200"', tag)

    @patch.object(
        plone.namedfile.scaling,
        "get_picture_variants",
        new=patch_Img2PictureTag_picture_variants,
        spec=True,
    )
    @patch.object(
        plone.namedfile.picture,
        "get_allowed_scales",
        new=patch_Img2PictureTag_allowed_scales,
        spec=True,
    )
    @patch.object(plone.namedfile.picture, "uuidToObject", spec=True)
    def testGetPictureTagWithAltAndTitle(self, mock_uuid_to_object):
        ImageScaling._sizes = patch_Img2PictureTag_allowed_scales()
        mock_uuid_to_object.return_value = self.item
        tag = self.scaling.picture(
            "image",
            picture_variant="medium",
            alt="Alternative text",
            title="Custom title",
        )
        base = self.item.absolute_url()
        expected = f"""<picture>
 <source srcset="{base}/@@images/image-600-....png 600w,
{base}/@@images/image-400-....png 400w,
{base}/@@images/image-800-....png 800w,
{base}/@@images/image-1000-....png 1000w,
{base}/@@images/image-1200-....png 1200w"/>
 <img...src="{base}/@@images/image-600-....png".../>
</picture>"""
        self.assertTrue(_ellipsis_match(expected, tag.strip()))

        # The exact placement of the img tag attributes can differ, especially
        # with different beautifulsoup versions.
        # So check here that all attributes are present.
        self.assertIn('alt="Alternative text"', tag)
        self.assertIn('height="200"', tag)
        self.assertIn('loading="lazy"', tag)
        self.assertIn('title="Custom title"', tag)
        self.assertIn('width="200"', tag)

    @patch.object(
        plone.namedfile.scaling,
        "get_picture_variants",
        new=patch_Img2PictureTag_empty_picture_variants,
        spec=True,
    )
    @patch.object(
        plone.namedfile.picture,
        "get_allowed_scales",
        new=patch_Img2PictureTag_allowed_scales,
        spec=True,
    )
    @patch.object(plone.namedfile.picture, "uuidToObject", spec=True)
    def testGetPictureTagWithoutAnyVariants(self, mock_uuid_to_object):
        ImageScaling._sizes = patch_Img2PictureTag_allowed_scales()
        mock_uuid_to_object.return_value = self.item
        tag = self.scaling.picture("image", picture_variant="medium")
        expected = """<img...src="http://nohost/item/@@images/image-0-....png".../>"""
        self.assertTrue(_ellipsis_match(expected, tag.strip()))

        # The exact placement of the img tag attributes can differ, especially
        # with different beautifulsoup versions.
        # So check here that all attributes are present.
        self.assertIn('height="200"', tag)
        self.assertIn('title="foo"', tag)
        self.assertIn('width="200"', tag)

    def testGetUnknownScale(self):
        foo = self.scaling.scale("image", scale="foo?")
        self.assertEqual(foo, None)

    def testScaleInvalidation(self):
        dt = self.item.modified()

        # Test that different parameters give different scale
        self.item.modified = lambda: dt
        scale1a = self.scaling.scale("image", width=100, height=80)
        scale2a = self.scaling.scale("image", width=80, height=60)
        self.assertNotEqual(scale1a.data, scale2a.data)

        # Test that bare object modification does not invalidate scales
        self.item.modified = lambda: dt + 1
        scale1b = self.scaling.scale("image", width=100, height=80)
        scale2b = self.scaling.scale("image", width=80, height=60)
        self.assertNotEqual(scale1b.data, scale2b.data)
        self.assertEqual(scale1a.data, scale1b.data)
        self.assertEqual(scale2a.data, scale2b.data)

        # Test changing _p_mtime on the field no longer invalidates a scale
        self.item.image._p_mtime = (dt + 1).millis()
        scale1b = self.scaling.scale("image", width=100, height=80)
        scale2b = self.scaling.scale("image", width=80, height=60)
        self.assertNotEqual(scale1b.data, scale2b.data)
        self.assertEqual(scale1a.data, scale1b.data)
        self.assertEqual(scale2a.data, scale2b.data)

        # Test changing the fields modified timestamp invalidates scales
        self.item.image._modified = (dt + 1).millis()
        scale1c = self.scaling.scale("image", width=100, height=80)
        scale2c = self.scaling.scale("image", width=80, height=60)
        self.assertNotEqual(scale1c.data, scale2c.data)
        self.assertNotEqual(scale1a.data, scale1c.data, "scale not updated?")
        self.assertNotEqual(scale2a.data, scale2c.data, "scale not updated?")

    def testFallBackToDatabaseModifiedTimeStamp(self):
        dt = self.item.modified()
        scale_a = self.scaling.scale("image", width=100, height=80)

        delattr(self.item.image, "_modified")

        # Since there is no _modified timestamp, _p_mtime is the fallback.
        self.item.image._p_mtime = (dt + 1).millis()
        scale_b = self.scaling.scale("image", width=100, height=80)
        self.assertNotEqual(scale_a.data, scale_b.data)

    def testCustomSizeChange(self):
        # set custom image sizes & view a scale
        self.scaling.available_sizes = {"foo": (23, 23)}
        foo = self.scaling.scale("image", scale="foo")
        self.assertEqual(foo.width, 23)
        self.assertEqual(foo.height, 23)
        # now let's update the scale dimensions, after which the scale
        # shouldn't be the same...
        self.scaling.available_sizes = {"foo": (42, 42)}
        foo = self.scaling.scale("image", scale="foo")
        self.assertEqual(foo.width, 42)
        self.assertEqual(foo.height, 42)

    def testDefaultAvailableSizes(self):
        # by default, no named scales are configured
        self.assertEqual(self.scaling.available_sizes, {})

    def testCustomAvailableSizes(self):
        # a callable can be used to look up the available sizes
        def custom_available_sizes():
            return {"bar": (10, 10)}

        sm = getSiteManager()
        sm.registerUtility(component=custom_available_sizes, provided=IAvailableSizes)
        self.assertEqual(self.scaling.available_sizes, {"bar": (10, 10)})
        sm.unregisterUtility(provided=IAvailableSizes)
        # for testing purposes, the sizes may also be set directly on
        # the scaling adapter
        self.scaling.available_sizes = {"qux": (12, 12)}
        self.assertEqual(self.scaling.available_sizes, {"qux": (12, 12)})

    def testGuardedAccess(self):
        # make sure it's not possible to access scales of forbidden images
        self.item.__allow_access_to_unprotected_subobjects__ = 0
        self.assertRaises(Unauthorized, self.scaling.guarded_orig_image, "image")
        self.item.__allow_access_to_unprotected_subobjects__ = 1

    def testGetAvailableSizes(self):
        self.scaling.available_sizes = {"foo": (60, 60)}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("once")
            self.assertEqual(
                self.scaling.getAvailableSizes(),
                {"foo": (60, 60)},
            )
            self.assertEqual(len(w), 1)
            self.assertIs(w[0].category, DeprecationWarning)
            self.assertIn(
                "use property available_sizes instead",
                str(w[0].message),
            )
            self.assertEqual(
                self.scaling.getAvailableSizes("image"),
                {"foo": (60, 60)},
            )
            self.assertEqual(len(w), 2)
            self.assertIs(w[1].category, DeprecationWarning)
            self.assertIn(
                "fieldname was passed to deprecated getAvailableSizes, but "
                "will be ignored.",
                str(w[1].message),
            )

    def testGetImageSize(self):
        assert self.scaling.getImageSize("image") == (200, 200)

    def testGetOriginalScaleTag(self):
        tag = self.scaling.tag("image")
        base = self.item.absolute_url()
        expected = (
            r'<img src="{}/@@images/({}).(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" />'.format(
                base, PAT_UID_SCALE
            )
        )
        self.assertTrue(re.match(expected, tag).groups())

    def testScaleOnItemWithNonASCIITitle(self):
        self.item.title = "ü"
        tag = self.scaling.tag("image")
        base = self.item.absolute_url()
        expected = (
            r'<img src="{}/@@images/({}).(jpeg|gif|png)" '
            r'alt="\xfc" title="\xfc" height="(\d+)" width="(\d+)" />'.format(
                base, PAT_UID_SCALE
            )
        )
        self.assertTrue(re.match(expected, tag).groups())

    def testScaleOnItemWithUnicodeTitle(self):
        self.item.Title = lambda: "ü"
        tag = self.scaling.tag("image")
        base = self.item.absolute_url()
        expected = (
            r'<img src="{}/@@images/({}).(jpeg|gif|png)" '
            r'alt="\xfc" title="\xfc" height="(\d+)" width="(\d+)" />'.format(
                base, PAT_UID_SCALE
            )
        )
        self.assertTrue(re.match(expected, tag).groups())

    def testScaledJpegImageQuality(self):
        """Test image quality setting for jpeg images.

        Image quality is not available for PNG images.
        """
        dt = DateTime()
        data = getFile("image.jpg")
        item = DummyContent()
        item.image = NamedImage(data, "image/png", "image.jpg")
        item.image._modified = dt.millis()
        scaling = ImageScaling(item, None)

        # scale an image, record its size
        foo = scaling.scale("image", width=100, height=80)
        size_foo = foo.data.getSize()
        # Let's pretend the imaging control panel sets the scaling quality to
        # "really sloppy"
        gsm = getGlobalSiteManager()
        qualitySupplier = DummyQualitySupplier()
        gsm.registerUtility(qualitySupplier.getQuality, IScaledImageQuality)
        item.image._modified = (dt + 1).millis()
        # now scale again
        bar = scaling.scale("image", width=100, height=80)
        size_bar = bar.data.getSize()
        # first one should be bigger
        self.assertTrue(size_foo > size_bar)

    def testOversizedHighPixelDensityScale(self):
        orig_size = max(self.scaling.getImageSize("image"))
        scale_size = orig_size / 2
        self.scaling.getHighPixelDensityScales = lambda: [
            {"scale": 2, "quality": 66},
            {"scale": 3, "quality": 66},
        ]
        foo = self.scaling.scale(
            "image", width=scale_size, height=scale_size, include_srcset=True
        )
        self.assertEqual(len(foo.srcset), 1)
        self.assertEqual(foo.srcset[0]["scale"], 2)


class ImageTraverseTests(unittest.TestCase):

    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer["app"]
        data = getFile("image.png")
        item = DummyContent()
        item.image = NamedImage(data, "image/png", "image.png")
        self.app._setOb("item", item)
        self.item = self.app.item
        self._orig_sizes = ImageScaling._sizes

    def tearDown(self):
        ImageScaling._sizes = self._orig_sizes

    def traverse(self, path=""):
        view = self.item.unrestrictedTraverse("@@images")
        stack = path.split("/")
        name = stack.pop(0)
        static_traverser = view.traverse(name, stack)
        scale = stack.pop(0)
        tag = static_traverser.traverse(scale, stack)
        base = self.item.absolute_url()
        expected = (
            r'<img src="{0}/@@images/([0-9a-z]*-[0-9]*-[0-9a-f]{{32}}).(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" />'.format(
                base,
            )
        )
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)
        uid, ext, height, width = groups
        return uid, ext, int(width), int(height)

    def testImageThumb(self):
        ImageScaling._sizes = {"thumb": (128, 128)}
        uid, ext, width, height = self.traverse("image/thumb")
        self.assertEqual((width, height), ImageScaling._sizes["thumb"])
        self.assertEqual(ext, "png")

    def testCustomSizes(self):
        # set custom image sizes
        ImageScaling._sizes = {"foo": (23, 23)}
        # make sure traversing works with the new sizes
        uid, ext, width, height = self.traverse("image/foo")
        self.assertEqual(width, 23)
        self.assertEqual(height, 23)

    def testScaleInvalidation(self):
        # first view the thumbnail of the original image
        ImageScaling._sizes = {"thumb": (128, 128)}
        uid1, ext, width1, height1 = self.traverse("image/thumb")
        wait_to_ensure_modified()
        # now upload a new one and make sure the thumbnail has changed
        data = getFile("image.jpg")
        self.item.image = NamedImage(data, "image/jpeg", "image.jpg")
        uid2, ext, width2, height2 = self.traverse("image/thumb")
        self.assertNotEqual(uid1, uid2, "thumb not updated?")
        # the height also differs as the original image had a size of 200, 200
        # whereas the updated one has 500, 200...
        self.assertEqual(width1, width2)
        self.assertNotEqual(height1, height2)

    def testCustomSizeChange(self):
        # set custom image sizes & view a scale
        ImageScaling._sizes = {"foo": (23, 23)}
        uid1, ext, width, height = self.traverse("image/foo")
        self.assertEqual(width, 23)
        self.assertEqual(height, 23)
        # now let's update the scale dimensions, after which the scale
        # should also have been updated...
        ImageScaling._sizes = {"foo": (42, 42)}
        uid2, ext, width, height = self.traverse("image/foo")
        self.assertEqual(width, 42)
        self.assertEqual(height, 42)
        self.assertNotEqual(uid1, uid2, "scale not updated?")

    def testGuardedAccess(self):
        # make sure it's not possible to access scales of forbidden images
        self.item.__allow_access_to_unprotected_subobjects__ = 0
        ImageScaling._sizes = {"foo": (42, 42)}
        self.assertRaises(Unauthorized, self.traverse, "image/foo")
        self.item.__allow_access_to_unprotected_subobjects__ = 1


class StorageTests(unittest.TestCase):
    """Test the scale storage.

    Especially test that we get an adapter for IImageScaleStorage
    instead of defaulting to plone.scale.storage.AnnotationStorage.
    """

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def setUp(self):
        sm = getSiteManager()
        sm.registerAdapter(FakeImageScaleStorage, (FakeImage, Interface))

    def tearDown(self):
        sm = getSiteManager()
        sm.unregisterAdapter(FakeImageScaleStorage, (FakeImage, Interface))

    def test_original(self):
        item = FakeImage("abcdef", "jpeg")
        scaling = ImageScaling(item, None)
        original = scaling.scale("image")
        self.assertEqual(original.data.value, "abcdef")
        self.assertIs(original.data, item)
        self.assertEqual(original.mimetype, "image/jpeg")
        self.assertIsInstance(original.mimetype, str)
        self.assertEqual(original.data.contentType, "image/jpeg")
        self.assertIsInstance(original.data.contentType, str)
        self.assertEqual(original.width, 6)
        self.assertEqual(original.height, 4)

        # Try the tag
        self.assertEqual(
            scaling.tag("image"),
            '<img src="http://fake.image/@@images/image.jpeg" alt="Image Title" title="Image Title" height="4" width="6" />',
        )

        # Try to access the item via uid.
        # This should fail, because we only have the original, not a scale.
        with self.assertRaises(NotFound):
            scaling.publishTraverse(self.layer["request"], "uid-0")

    def test_width(self):
        # For FakeImage scales, the width changes the mimetype/format.
        item = FakeImage("abcdef", "jpeg")
        scaling = ImageScaling(item, None)
        scale = scaling.scale("image", width=2)
        self.assertEqual(scale.data.value, "abcdef")
        self.assertIsInstance(scale.data, FakeImage)
        self.assertEqual(scale.mimetype, "image/jp")
        self.assertEqual(scale.data.contentType, "image/jp")
        self.assertEqual(scale.width, 6)
        self.assertEqual(scale.height, 2)

        # Ask for the same scale and you get the same FakeImage.
        scale2 = scaling.scale("image", width=2)
        self.assertIs(scale.data, scale2.data)

        # Try the tag.  It should have a uid.
        self.assertEqual(
            scaling.tag("image", width=2),
            '<img src="http://fake.image/@@images/uid-0.jp" alt="Image Title" title="Image Title" height="2" width="6" />',
        )

        # Access the item via uid.
        scale_uid = scaling.publishTraverse(self.layer["request"], "uid-0")
        self.assertEqual(scale_uid.data.uid, "uid-0")
        self.assertEqual(scale_uid.data.info["uid"], "uid-0")
        self.assertIs(scale_uid.data, scale2.data)

    def test_height(self):
        # For FakeImage scales, the height changes the value.
        item = FakeImage("abcdef", "jpeg")
        scaling = ImageScaling(item, None)
        scale = scaling.scale("image", height=3)
        self.assertEqual(scale.data.value, "abc")
        self.assertIsInstance(scale.data, FakeImage)
        self.assertEqual(scale.mimetype, "image/jpeg")
        self.assertEqual(scale.data.contentType, "image/jpeg")
        self.assertEqual(scale.width, 3)
        self.assertEqual(scale.height, 4)

        # Ask for the same scale and you get the same FakeImage.
        scale2 = scaling.scale("image", height=3)
        self.assertIs(scale.data, scale2.data)

        # Try the tag.  It should have a uid.
        self.assertEqual(
            scaling.tag("image", height=3),
            '<img src="http://fake.image/@@images/uid-0.jpeg" alt="Image Title" title="Image Title" height="4" width="3" />',
        )

        # Access the item via uid.
        scale_uid = scaling.publishTraverse(self.layer["request"], "uid-0")
        self.assertEqual(scale_uid.data.uid, "uid-0")
        self.assertEqual(scale_uid.data.info["uid"], "uid-0")
        self.assertIs(scale_uid.data, scale2.data)

    def test_title(self):
        # Test that a custom title property on an ImageScale class is used.
        item = FakeImage("abcdef", "jpeg")
        scaling = ImageScaling(item, None)
        scaling._scale_view_class = TitleImageScale
        self.assertEqual(
            scaling.tag("image"),
            '<img src="http://fake.image/@@images/image.jpeg" alt="title from class" title="title from class" height="4" width="6" />',
        )
        self.assertEqual(
            scaling.tag("image", alt="own alt"),
            '<img src="http://fake.image/@@images/image.jpeg" alt="own alt" title="title from class" height="4" width="6" />',
        )
        self.assertEqual(
            scaling.tag("image", title="own title"),
            '<img src="http://fake.image/@@images/image.jpeg" alt="title from class" title="own title" height="4" width="6" />',
        )
        self.assertEqual(
            scaling.tag("image", alt="own alt", title="own title"),
            '<img src="http://fake.image/@@images/image.jpeg" alt="own alt" title="own title" height="4" width="6" />',
        )


class Img2PictureTagTests(unittest.TestCase):
    """Low level tests for Img2PictureTag."""

    def _makeOne(self):
        return plone.namedfile.picture.Img2PictureTag()

    def test_update_src_scale(self):
        update_src_scale = self._makeOne().update_src_scale
        self.assertEqual(
            update_src_scale("foo/fieldname/old", "new"), "foo/fieldname/new"
        )
        self.assertEqual(
            update_src_scale("@@images/fieldname/old", "mini"),
            "@@images/fieldname/mini",
        )
        self.assertEqual(
            update_src_scale("@@images/fieldname", "preview"),
            "@@images/fieldname/preview",
        )
        self.assertEqual(
            update_src_scale(
                "photo.jpg/@@images/image-1200-4a03b0a8227d28737f5d9e3e481bdbd6.jpeg",
                "teaser",
            ),
            "photo.jpg/@@images/image/teaser",
        )


def test_suite():
    from unittest import defaultTestLoader

    return defaultTestLoader.loadTestsFromName(__name__)
