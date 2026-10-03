from bs4 import BeautifulSoup
from DateTime import DateTime
from io import BytesIO
from OFS.SimpleItem import SimpleItem
from plone import schema
from plone.base.interfaces import IImageScalesFieldAdapter
from plone.base.interfaces import IImagingSchema
from plone.dexterity.content import Item
from plone.namedfile.field import NamedImage as NamedImageField
from plone.namedfile.file import NamedImage
from plone.namedfile.interfaces import IAvailableSizes
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.namedfile.picture import Img2PictureTag
from plone.namedfile.scaling import ImageScaling
from plone.namedfile.scaling import NavigationRootScaling
from plone.namedfile.testing import PLONE_NAMEDFILE_INTEGRATION_TESTING
from plone.namedfile.tests import getFile
from plone.namedfile.utils import avif_available
from plone.namedfile.utils import AVIF_SUFFIX
from plone.namedfile.utils import get_avif_mode
from plone.namedfile.utils import get_avif_quality
from plone.namedfile.utils import get_avif_speed
from plone.namedfile.utils import getAllowedSizes
from plone.namedfile.utils import getQuality
from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from plone.scale.interfaces import IScaledImageQuality
from plone.scale.scale import scaleImage
from unittest import mock
from zope.annotation import IAttributeAnnotatable
from zope.component import getGlobalSiteManager
from zope.component import getMultiAdapter
from zope.interface import implementer
from zope.interface import Interface
from zope.publisher.interfaces import NotFound

import PIL.Image
import plone.namedfile.picture
import plone.namedfile.scaling
import plone.namedfile.utils
import re
import unittest

STABLE = re.compile(r"/@@images/image-\d+-[0-9a-f]{32}\.\w+$")
STABLE_AVIF = re.compile(r"/@@images/image-\d+-[0-9a-f]{32}\.avif$")
# The catalog metadata stores the path below the object.
STABLE_AVIF_PATH = re.compile(r"^@@images/image-\d+-[0-9a-f]{32}\.avif$")


def is_avif(data):
    return data[4:12] == b"ftypavif"


def is_jpeg(data):
    return data[:3] == b"\xff\xd8\xff"


def is_png(data):
    return data[:4] == b"\x89PNG"


def avif_bytes(mode="RGB"):
    color = (30, 120, 200, 128) if mode == "RGBA" else (30, 120, 200)
    out = BytesIO()
    PIL.Image.new(mode, (640, 480), color).save(out, "AVIF")
    return out.getvalue()


def png_image():
    return NamedImage(getFile("image.png"), "image/png", "image.png")


def svg_image():
    return NamedImage(getFile("image.svg"), "image/svg+xml", "image.svg")


def avif_image(mode="RGB"):
    return NamedImage(avif_bytes(mode), filename="pic.avif")


def soup(markup):
    return BeautifulSoup(str(markup), "html.parser")


def sources(markup):
    return soup(markup).find_all("source")


def srcset_urls(source):
    return [candidate.split()[0] for candidate in source["srcset"].split(",")]


@implementer(IAttributeAnnotatable, IImageScaleTraversable)
class DummyContent(SimpleItem):
    image = None
    modified = DateTime
    id = __name__ = "item"
    title = "foo"

    def Title(self):
        return self.title

    def UID(self):
        return "dummy_uuid"


class FakeBrain:
    Title = "foo"

    def __init__(self, url, content_type="image/png", download=None):
        self.url = url
        self.image_scales = {
            "image": [
                {
                    "content-type": content_type,
                    "scales": {
                        "thumb": {
                            "download": download or "@@images/image-128-abc.png",
                            "width": 128,
                            "height": 128,
                            "avif": {"download": "@@images/image-128-abc.avif"},
                        }
                    },
                }
            ]
        }

    def getURL(self):
        return self.url


@unittest.skipUnless(avif_available(), "Pillow cannot encode AVIF")
class AvifModeTestCase(unittest.TestCase):
    """Image scales under one AVIF mode, with the imaging settings in a
    registry like a Plone site has."""

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING
    mode = "avif_with_fallback"

    def setUp(self):
        self.request = self.layer["request"]
        self.registry = Registry()
        self.registry.registerInterface(IImagingSchema, prefix="plone")
        self.registry["plone.avif_mode"] = self.mode
        self.sm = getGlobalSiteManager()
        self.sm.registerUtility(self.registry, IRegistry)
        self.sm.registerUtility(getAllowedSizes, IAvailableSizes)
        self.sm.registerUtility(getQuality, IScaledImageQuality)
        item = DummyContent()
        item.image = self.upload()
        self.layer["app"]._setOb("item", item)
        self.item = self.layer["app"].item
        self.images = ImageScaling(self.item, self.request)

    def tearDown(self):
        self.sm.unregisterUtility(self.registry, IRegistry)
        self.sm.unregisterUtility(getAllowedSizes, IAvailableSizes)
        self.sm.unregisterUtility(getQuality, IScaledImageQuality)

    def upload(self):
        return png_image()

    def traverse(self, *path):
        self.request["TraversalRequestNameStack"] = list(reversed(path[1:]))
        return self.images.publishTraverse(self.request, path[0])

    def serve(self, url):
        return self.traverse(url.rsplit("/", 1)[-1]).index_html()

    def image_scales_metadata(self, image):
        """The image_scales catalog metadata of a Dexterity item holding
        ``image``, and the @@images view of that item."""
        content = Item()
        field = NamedImageField()
        field.__name__ = "image"
        field.set(content, image)
        adapter = getMultiAdapter(
            (field, content, self.request), IImageScalesFieldAdapter
        )
        (info,) = adapter()
        return info, ImageScaling(content, self.request)

    def img(self, markup):
        self.assertTrue(str(markup).startswith("<img "), markup)
        return soup(markup).img

    def picture(self):
        # The layer has no catalog to resolve the item's UID with.
        with mock.patch.object(
            plone.namedfile.picture, "uuidToObject", return_value=self.item
        ):
            return self.images.picture("image", picture_variant="small")

    def scale_kwargs(self, *args, **kwargs):
        with mock.patch.object(
            plone.namedfile.scaling, "scaleImage", wraps=scaleImage
        ) as scaled:
            self.images.scale(*args, **kwargs)
        return scaled.call_args.kwargs


class AvifWithFallbackTests(AvifModeTestCase):
    def test_plain_scale_keeps_the_original_format(self):
        scale = self.images.scale("image", "teaser")
        self.assertEqual(scale.mimetype, "image/png")
        self.assertTrue(scale.url.endswith(".png"), scale.url)

    def test_avif_scale_name_scales_to_avif(self):
        scale = self.images.scale("image", "teaser.avif")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertTrue(is_avif(scale.data.data))
        self.assertTrue(scale.url.endswith(".avif"), scale.url)
        self.assertEqual((scale.width, scale.height), (200, 200))

    def test_avif_scale_is_keyed_on_its_format_not_its_quality(self):
        # Like the JPEG quality, the AVIF quality and speed are site settings,
        # not part of a scale's identity.
        key = dict(self.images.scale("image", "teaser.avif").key)
        self.assertEqual(key["target_format"], "AVIF")
        self.assertNotIn("quality", key)
        self.assertNotIn("speed", key)

    def test_avif_scale_is_encoded_with_the_registry_quality_and_speed(self):
        self.registry["plone.avif_quality"] = 40
        self.registry["plone.avif_speed"] = 3
        kwargs = self.scale_kwargs("image", "teaser.avif")
        self.assertEqual(kwargs["target_format"], "AVIF")
        self.assertEqual(kwargs["quality"], 40)
        self.assertEqual(kwargs["speed"], 3)

    def test_plain_scale_is_encoded_with_the_jpeg_quality(self):
        self.registry["plone.avif_quality"] = 40
        kwargs = self.scale_kwargs("image", "teaser")
        self.assertEqual(kwargs["quality"], 88)
        self.assertNotIn("target_format", kwargs)
        self.assertNotIn("speed", kwargs)

    def test_avif_pre_scale_has_a_stable_avif_url(self):
        twin = self.images.scale("image", "preview.avif", pre=True)
        plain = self.images.scale("image", "preview", pre=True)
        self.assertRegex(twin.url, STABLE_AVIF)
        self.assertNotEqual(twin.uid, plain.uid)
        self.assertTrue(plain.url.endswith(".png"), plain.url)

    def test_stable_avif_url_serves_avif_inline(self):
        twin = self.images.scale("image", "preview.avif", pre=True)
        self.assertTrue(is_avif(self.serve(twin.url)))
        response = self.request.response
        self.assertEqual(response.getHeader("Content-Type"), "image/avif")
        self.assertIsNone(response.getHeader("Content-Disposition"))

    def test_named_avif_url_serves_avif(self):
        self.assertTrue(is_avif(self.traverse("image", "preview.avif").index_html()))

    def test_unknown_scale_with_avif_suffix_is_not_found(self):
        self.assertIsNone(self.images.scale("image", "nosuchscale.avif"))

    def test_svg_has_no_avif_scale(self):
        self.item.image = svg_image()
        self.assertIsNone(self.images.scale("image", "preview.avif"))
        self.assertEqual(
            self.images.scale("image", "preview").mimetype, "image/svg+xml"
        )

    def test_tag_is_a_plain_img(self):
        markup = self.images.tag("image", scale="thumb", css_class="thumb")
        img = self.img(markup)
        self.assertTrue(img["src"].endswith(".png"), img["src"])
        self.assertEqual(img["class"], ["thumb"])

    def test_high_pixel_density_srcset_keeps_the_original_format(self):
        self.images.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        img = self.img(self.images.tag("image", width=50, height=50))
        self.assertTrue(img["srcset"].endswith(".png 2x"), img["srcset"])

    def test_brain_tag_is_a_plain_img(self):
        view = NavigationRootScaling(self.item, self.request)
        markup = view._tag_from_brain_image_scales(
            FakeBrain("http://nohost/item"), "image", scale="thumb"
        )
        img = self.img(markup)
        self.assertEqual(img["src"], "http://nohost/item/@@images/image-128-abc.png")
        self.assertNotIn(".avif", str(markup))

    def test_image_scales_metadata_carries_avif_twins(self):
        info, images = self.image_scales_metadata(png_image())
        self.assertTrue(info["download"].endswith(".png"), info["download"])
        self.assertNotIn("avif", info)
        self.assertTrue(info["scales"])
        for name, scale in info["scales"].items():
            self.assertTrue(scale["download"].endswith(".png"), scale)
            twin = scale["avif"]["download"]
            self.assertRegex(twin, STABLE_AVIF_PATH)
            # The stored scale that "<name>.avif" serves, not a second one.
            named = images.scale("image", f"{name}{AVIF_SUFFIX}", pre=True)
            self.assertEqual(twin, named.url.lstrip("/"))

    def test_svg_image_scales_metadata_has_no_avif_twins(self):
        info, _ = self.image_scales_metadata(svg_image())
        self.assertTrue(info["scales"])
        for scale in info["scales"].values():
            self.assertNotIn("avif", scale)

    def test_picture_offers_avif_in_front_of_each_source(self):
        markup = self.picture()
        avif, original = sources(markup)
        self.assertEqual(avif["type"], "image/avif")
        self.assertIsNone(original.get("type"))
        self.assertEqual(avif["sizes"], original["sizes"])
        for url in srcset_urls(avif):
            self.assertRegex(url, STABLE_AVIF)
        for url in srcset_urls(original):
            self.assertRegex(url, STABLE)
            self.assertTrue(url.endswith(".png"), url)
        self.assertTrue(soup(markup).img["src"].endswith(".png"))
        self.assertTrue(is_avif(self.serve(srcset_urls(avif)[0])))

    def test_svg_picture_has_no_avif_source(self):
        self.item.image = svg_image()
        self.assertEqual(len(sources(self.picture())), 1)


class AvifUploadWithFallbackTests(AvifModeTestCase):
    """An AVIF upload is offered as AVIF, with a JPEG fallback for browsers
    that cannot show AVIF."""

    def upload(self):
        return avif_image()

    def test_upload_is_avif(self):
        self.assertEqual(self.item.image.contentType, "image/avif")

    def test_plain_scale_is_jpeg(self):
        scale = self.images.scale("image", "teaser")
        self.assertEqual(scale.mimetype, "image/jpeg")
        self.assertTrue(is_jpeg(scale.data.data))

    def test_plain_scale_is_keyed_on_the_fallback_format(self):
        key = dict(self.images.scale("image", "teaser").key)
        self.assertEqual(key["target_format"], "JPEG")
        self.assertNotIn("quality", key)

    def test_plain_scale_is_encoded_with_the_jpeg_quality(self):
        self.registry["plone.avif_quality"] = 40
        kwargs = self.scale_kwargs("image", "teaser")
        self.assertEqual(kwargs["target_format"], "JPEG")
        self.assertEqual(kwargs["quality"], 88)
        self.assertNotIn("speed", kwargs)

    def test_plain_pre_scale_has_a_jpeg_url_and_serves_jpeg(self):
        scale = self.images.scale("image", "preview", pre=True)
        self.assertRegex(scale.url, STABLE)
        self.assertTrue(scale.url.endswith(".jpeg"), scale.url)
        self.assertTrue(is_jpeg(self.serve(scale.url)))

    def test_avif_scale_name_stays_avif(self):
        scale = self.images.scale("image", "teaser.avif")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertTrue(is_avif(scale.data.data))

    def test_tag_is_a_plain_img_pointing_at_jpeg(self):
        img = self.img(self.images.tag("image", scale="teaser"))
        self.assertRegex(img["src"], STABLE)
        self.assertTrue(is_jpeg(self.serve(img["src"])))

    def test_tag_of_the_original_is_a_full_size_jpeg(self):
        img = self.img(self.images.tag("image"))
        self.assertEqual(img["width"], "640")
        self.assertTrue(is_jpeg(self.serve(img["src"])))

    def test_high_pixel_density_srcset_is_jpeg(self):
        self.images.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        img = self.img(self.images.tag("image", scale="thumb"))
        url = img["srcset"].split()[0]
        self.assertRegex(url, STABLE)
        self.assertTrue(is_jpeg(self.serve(url)))

    def test_alpha_falls_back_to_png(self):
        self.item.image = avif_image("RGBA")
        img = self.img(self.images.tag("image", scale="teaser"))
        self.assertTrue(is_png(self.serve(img["src"])))

    def test_picture_offers_avif_with_a_jpeg_fallback(self):
        markup = self.picture()
        avif, fallback = sources(markup)
        self.assertEqual(avif["type"], "image/avif")
        for url in srcset_urls(avif):
            self.assertRegex(url, STABLE_AVIF)
        self.assertTrue(is_avif(self.serve(srcset_urls(avif)[0])))
        for url in srcset_urls(fallback):
            self.assertRegex(url, STABLE)
        self.assertTrue(is_jpeg(self.serve(srcset_urls(fallback)[0])))
        self.assertTrue(is_jpeg(self.serve(soup(markup).img["src"])))

    def test_image_scales_metadata_has_jpeg_scales_with_avif_twins(self):
        info, images = self.image_scales_metadata(avif_image())
        self.assertEqual(info["content-type"], "image/avif")
        self.assertTrue(info["download"].endswith(".jpeg"), info["download"])
        self.assertTrue(info["scales"])
        for name, scale in info["scales"].items():
            self.assertTrue(scale["download"].endswith(".jpeg"), scale)
            twin = scale["avif"]["download"]
            self.assertRegex(twin, STABLE_AVIF_PATH)
            named = images.scale("image", f"{name}{AVIF_SUFFIX}", pre=True)
            self.assertEqual(twin, named.url.lstrip("/"))


class AvifOnlyTests(AvifModeTestCase):
    mode = "avif_only"

    def test_plain_scale_is_avif(self):
        scale = self.images.scale("image", "teaser")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertTrue(is_avif(scale.data.data))
        self.assertTrue(scale.url.endswith(".avif"), scale.url)
        self.assertEqual(dict(scale.key)["target_format"], "AVIF")

    def test_avif_scale_name_is_the_same_scale(self):
        self.assertEqual(
            self.images.scale("image", "teaser").uid,
            self.images.scale("image", "teaser.avif").uid,
        )

    def test_plain_scale_is_encoded_with_the_avif_quality_and_speed(self):
        self.registry["plone.avif_quality"] = 40
        self.registry["plone.avif_speed"] = 3
        kwargs = self.scale_kwargs("image", "teaser")
        self.assertEqual(kwargs["target_format"], "AVIF")
        self.assertEqual(kwargs["quality"], 40)
        self.assertEqual(kwargs["speed"], 3)

    def test_tag_is_a_plain_img_pointing_at_avif(self):
        img = self.img(self.images.tag("image", scale="thumb"))
        self.assertRegex(img["src"], STABLE_AVIF)
        self.assertTrue(is_avif(self.serve(img["src"])))

    def test_tag_of_the_original_is_a_full_size_avif(self):
        img = self.img(self.images.tag("image"))
        self.assertRegex(img["src"], STABLE_AVIF)
        self.assertEqual(img["width"], "200")
        self.assertTrue(is_avif(self.serve(img["src"])))

    def test_high_pixel_density_srcset_is_avif(self):
        self.images.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        img = self.img(self.images.tag("image", width=50, height=50))
        url = img["srcset"].split()[0]
        self.assertRegex(url, STABLE_AVIF)
        self.assertTrue(is_avif(self.serve(url)))

    def test_svg_stays_svg(self):
        self.item.image = svg_image()
        self.assertEqual(self.images.scale("image", "teaser").mimetype, "image/svg+xml")
        self.assertIsNone(self.images.scale("image", "teaser.avif"))
        self.assertTrue(self.img(self.images.tag("image"))["src"].endswith(".svg"))

    def test_picture_has_avif_sources_and_no_twins(self):
        markup = self.picture()
        (source,) = sources(markup)
        for url in srcset_urls(source):
            self.assertRegex(url, STABLE_AVIF)
        self.assertRegex(soup(markup).img["src"], STABLE_AVIF)

    def test_image_scales_metadata_points_at_avif_without_twins(self):
        info, _ = self.image_scales_metadata(png_image())
        self.assertTrue(info["download"].endswith(".avif"), info["download"])
        self.assertTrue(info["scales"])
        for scale in info["scales"].values():
            self.assertTrue(scale["download"].endswith(".avif"), scale)
            self.assertNotIn("avif", scale)


class AvifUploadAvifOnlyTests(AvifModeTestCase):
    mode = "avif_only"

    def upload(self):
        return avif_image()

    def test_plain_scale_is_avif(self):
        scale = self.images.scale("image", "teaser")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertTrue(is_avif(scale.data.data))

    def test_original_is_served_as_uploaded(self):
        scale = self.images.scale("image")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertEqual(scale.data.data, self.item.image.data)


class AvifDisabledTests(AvifModeTestCase):
    mode = "disabled"

    def test_plain_scale_keeps_the_original_format(self):
        self.assertEqual(self.images.scale("image", "teaser").mimetype, "image/png")

    def test_avif_scale_name_is_not_found(self):
        self.assertIsNone(self.images.scale("image", "teaser.avif"))
        with self.assertRaises(NotFound):
            self.traverse("image", "teaser.avif")

    def test_tag_is_a_plain_img(self):
        img = self.img(self.images.tag("image", scale="thumb"))
        self.assertTrue(img["src"].endswith(".png"), img["src"])

    def test_picture_has_no_avif_source(self):
        markup = self.picture()
        self.assertEqual(len(sources(markup)), 1)
        self.assertNotIn(".avif", str(markup))

    def test_image_scales_metadata_has_no_avif_twins(self):
        info, _ = self.image_scales_metadata(png_image())
        self.assertTrue(info["scales"])
        for scale in info["scales"].values():
            self.assertTrue(scale["download"].endswith(".png"), scale)
            self.assertNotIn("avif", scale)


class AvifUploadDisabledTests(AvifModeTestCase):
    """Disabled means no conversion: an AVIF upload gets AVIF scales."""

    mode = "disabled"

    def upload(self):
        return avif_image()

    def test_plain_scale_is_avif(self):
        scale = self.images.scale("image", "teaser")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertTrue(is_avif(scale.data.data))
        self.assertTrue(scale.url.endswith(".avif"), scale.url)

    def test_plain_scale_is_not_asked_for_another_format(self):
        self.assertNotIn("target_format", self.scale_kwargs("image", "teaser"))
        self.assertNotIn(
            "target_format", dict(self.images.scale("image", "teaser").key)
        )

    def test_original_is_served_as_uploaded(self):
        scale = self.images.scale("image")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertEqual(scale.data.data, self.item.image.data)

    def test_avif_scale_name_is_not_found(self):
        self.assertIsNone(self.images.scale("image", "teaser.avif"))

    def test_tag_is_a_plain_img_pointing_at_avif(self):
        img = self.img(self.images.tag("image", scale="teaser"))
        self.assertRegex(img["src"], STABLE_AVIF)
        self.assertTrue(is_avif(self.serve(img["src"])))

    def test_high_pixel_density_srcset_is_avif(self):
        self.images.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        img = self.img(self.images.tag("image", scale="thumb"))
        url = img["srcset"].split()[0]
        self.assertRegex(url, STABLE_AVIF)
        self.assertTrue(is_avif(self.serve(url)))

    def test_alpha_stays_avif(self):
        self.item.image = avif_image("RGBA")
        img = self.img(self.images.tag("image", scale="teaser"))
        self.assertTrue(is_avif(self.serve(img["src"])))

    def test_picture_sources_are_the_avif_scales_without_twins(self):
        markup = self.picture()
        (source,) = sources(markup)
        self.assertIsNone(source.get("type"))
        for url in srcset_urls(source):
            self.assertRegex(url, STABLE_AVIF)
        self.assertTrue(is_avif(self.serve(srcset_urls(source)[0])))
        self.assertTrue(is_avif(self.serve(soup(markup).img["src"])))


class AvifPictureTagUrlTests(AvifModeTestCase):
    """Picture tags built from a scale URL alone, without resolving the
    image object, as the picture variants filter does for rich text."""

    def create(self, src="/plone/pic/@@images/image/teaser", media=None):
        source = {"scale": "teaser", "additionalScales": ["preview"]}
        if media:
            source["media"] = media
        return Img2PictureTag().create_picture_tag([source], {"src": src, "alt": ""})

    def test_sources_get_avif_twins_in_front(self):
        tag = self.create(media="(min-width: 768px)")
        avif, original = sources(tag)
        self.assertEqual(avif["type"], "image/avif")
        self.assertEqual(
            avif["srcset"],
            "/plone/pic/@@images/image/teaser.avif 600w,\n"
            "/plone/pic/@@images/image/preview.avif 400w",
        )
        self.assertEqual(avif["sizes"], original["sizes"])
        self.assertEqual(avif["media"], original["media"])
        self.assertIsNone(original.get("type"))
        self.assertNotIn(".avif", original["srcset"])
        self.assertNotIn(".avif", tag.img["src"])

    def test_urls_outside_images_get_no_twin(self):
        self.assertEqual(len(sources(self.create(src="/plone/some-image.png"))), 1)

    def test_disabled_mode_adds_no_twin(self):
        self.registry["plone.avif_mode"] = "disabled"
        self.assertNotIn(".avif", str(self.create()))

    def test_avif_only_mode_adds_no_twin(self):
        # The plain scale URLs serve AVIF in this mode.
        self.registry["plone.avif_mode"] = "avif_only"
        tag = self.create()
        self.assertEqual(len(sources(tag)), 1)
        self.assertNotIn(".avif", str(tag))


class AvifSettingsTests(unittest.TestCase):
    """The settings fall back to their defaults without a registry or with a
    plone.base that does not have them yet."""

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def test_defaults_without_a_registry(self):
        with mock.patch.object(plone.namedfile.utils, "avif_available", lambda: True):
            self.assertEqual(get_avif_mode(), "avif_with_fallback")
        self.assertEqual(get_avif_quality(), 65)
        self.assertEqual(get_avif_speed(), 8)

    def test_disabled_when_pillow_cannot_encode_avif(self):
        with mock.patch.object(plone.namedfile.utils, "avif_available", lambda: False):
            self.assertEqual(get_avif_mode(), "disabled")

    def test_defaults_when_the_schema_lacks_the_settings(self):
        class IOldImagingSchema(Interface):
            quality = schema.Int(default=88)

        registry = Registry()
        registry.registerInterface(IOldImagingSchema, prefix="plone")
        sm = getGlobalSiteManager()
        sm.registerUtility(registry, IRegistry)
        try:
            with (
                mock.patch.object(
                    plone.namedfile.utils, "IImagingSchema", IOldImagingSchema
                ),
                mock.patch.object(
                    plone.namedfile.utils, "avif_available", lambda: True
                ),
            ):
                self.assertEqual(get_avif_mode(), "avif_with_fallback")
                self.assertEqual(get_avif_quality(), 65)
                self.assertEqual(get_avif_speed(), 8)
        finally:
            sm.unregisterUtility(registry, IRegistry)
