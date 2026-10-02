from bs4 import BeautifulSoup
from DateTime import DateTime
from io import BytesIO
from OFS.SimpleItem import SimpleItem
from plone.namedfile.file import NamedImage
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.namedfile.picture import Img2PictureTag
from plone.namedfile.scaling import ImageScaling
from plone.namedfile.scaling import NavigationRootScaling
from plone.namedfile.testing import PLONE_NAMEDFILE_INTEGRATION_TESTING
from plone.namedfile.tests import getFile
from plone.namedfile.utils import avif_available
from unittest import mock
from zope.annotation import IAttributeAnnotatable
from zope.interface import implementer

import os
import PIL.Image
import plone.namedfile.picture
import re
import unittest

STABLE = re.compile(r"/@@images/image-\d+-[0-9a-f]{32}\.\w+$")
STABLE_AVIF = re.compile(r"/@@images/image-\d+-[0-9a-f]{32}\.avif$")
SIZES = {"teaser": (600, 65536), "preview": (400, 65536), "thumb": (128, 128)}


def is_avif(data):
    return data[4:12] == b"ftypavif"


def is_jpeg(data):
    return data[:3] == b"\xff\xd8\xff"


def avif_bytes(mode="RGB"):
    color = (30, 120, 200, 128) if mode == "RGBA" else (30, 120, 200)
    out = BytesIO()
    PIL.Image.new(mode, (640, 480), color).save(out, "AVIF")
    return out.getvalue()


def sources(markup):
    return BeautifulSoup(str(markup), "html.parser").find_all("source")


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
                        }
                    },
                }
            ]
        }

    def getURL(self):
        return self.url


@unittest.skipUnless(avif_available(), "Pillow cannot encode AVIF")
class AvifScaleTests(unittest.TestCase):
    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def setUp(self):
        self.request = self.layer["request"]
        item = DummyContent()
        item.image = NamedImage(getFile("image.png"), "image/png", "image.png")
        self.layer["app"]._setOb("item", item)
        self.item = self.layer["app"].item
        self._orig_sizes = ImageScaling._sizes
        ImageScaling._sizes = SIZES
        self.images = ImageScaling(self.item, self.request)

    def tearDown(self):
        ImageScaling._sizes = self._orig_sizes

    def traverse(self, *path):
        self.request["TraversalRequestNameStack"] = list(reversed(path[1:]))
        return self.images.publishTraverse(self.request, path[0])

    def test_avif_suffix_scales_to_avif(self):
        scale = self.images.scale("image", "teaser.avif")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertTrue(is_avif(scale.data.data))
        self.assertTrue(scale.url.endswith(".avif"), scale.url)
        self.assertEqual((scale.width, scale.height), (200, 200))

    def test_plain_scale_keeps_the_original_format(self):
        scale = self.images.scale("image", "teaser")
        self.assertEqual(scale.mimetype, "image/png")

    def test_avif_pre_scale_has_a_stable_avif_url(self):
        twin = self.images.scale("image", "preview.avif", pre=True)
        plain = self.images.scale("image", "preview", pre=True)
        self.assertRegex(twin.url, STABLE_AVIF)
        self.assertNotEqual(twin.uid, plain.uid)
        self.assertTrue(plain.url.endswith(".png"), plain.url)

    def test_stable_avif_url_serves_avif_inline(self):
        twin = self.images.scale("image", "preview.avif", pre=True)
        scale = self.traverse(twin.url.rsplit("/", 1)[-1])
        data = scale.index_html()
        self.assertTrue(is_avif(data))
        response = self.request.response
        self.assertEqual(response.getHeader("Content-Type"), "image/avif")
        self.assertIsNone(response.getHeader("Content-Disposition"))

    def test_named_avif_url_serves_avif(self):
        scale = self.traverse("image", "preview.avif")
        self.assertTrue(is_avif(scale.index_html()))

    def test_unknown_scale_with_avif_suffix_is_not_found(self):
        self.assertIsNone(self.images.scale("image", "nosuchscale.avif"))

    def test_avif_scale_is_keyed_on_its_own_quality(self):
        scale = self.images.scale("image", "teaser.avif")
        self.assertIn(("target_format", "AVIF"), scale.key)
        self.assertIn(("quality", 65), scale.key)

    def test_unscalable_bytes_value_has_no_scale(self):
        # e.g. a Bytes field fed by plone.formwidget.namedfile's converter
        self.item.image = b"filenameb64:aW1hZ2UuanBn;datab64:/9j/4AAQ"
        self.assertIsNone(self.images.scale("image", "preview"))

    def test_svg_has_no_avif_twin(self):
        self.item.image = NamedImage(getFile("image.svg"), "image/svg+xml", "i.svg")
        self.assertIsNone(self.images.scale("image", "preview.avif"))
        markup = self.images.tag("image", scale="preview")
        self.assertTrue(markup.startswith("<img"), markup)

    def test_tag_is_a_picture_with_an_avif_source(self):
        markup = self.images.tag("image", scale="thumb", css_class="thumb")
        picture = BeautifulSoup(markup, "html.parser").picture
        self.assertIsNotNone(picture, markup)
        self.assertEqual(picture.source["type"], "image/avif")
        self.assertRegex(picture.source["srcset"], STABLE_AVIF)
        self.assertTrue(picture.img["src"].endswith(".png"), picture.img["src"])
        self.assertEqual(picture.img["class"], ["thumb"])
        scale = self.traverse(picture.source["srcset"].rsplit("/", 1)[-1])
        self.assertTrue(is_avif(scale.index_html()))

    def test_tag_of_the_original_gets_a_full_size_twin(self):
        markup = self.images.tag("image")
        srcset = sources(markup)[0]["srcset"]
        scale = self.traverse(srcset.rsplit("/", 1)[-1])
        self.assertTrue(is_avif(scale.index_html()))
        self.assertEqual((scale.width, scale.height), (200, 200))

    def test_tag_with_high_pixel_density_twins(self):
        self.images.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        scale = self.images.scale("image", width=50, height=50, pre=True)
        twin_srcset = scale.avif_srcset()
        one_x, two_x = twin_srcset.split(", ")
        self.assertTrue(one_x.endswith(".avif 1x"), one_x)
        self.assertTrue(two_x.endswith(".avif 2x"), two_x)

    def test_env_variable_turns_twins_off(self):
        with mock.patch.dict(os.environ, {"NAMEDFILE_AVIF": "0"}):
            markup = self.images.tag("image", scale="thumb")
        self.assertTrue(markup.startswith("<img"), markup)
        # Serving AVIF scales keeps working: cached pages may point at them.
        self.assertIsNotNone(self.images.scale("image", "thumb.avif"))

    def test_brain_tag_gets_a_named_avif_twin(self):
        view = NavigationRootScaling(self.item, self.request)
        markup = view._tag_from_brain_image_scales(
            FakeBrain("http://nohost/item"), "image", scale="thumb"
        )
        picture = BeautifulSoup(markup, "html.parser").picture
        self.assertIsNotNone(picture, markup)
        self.assertEqual(
            picture.source["srcset"], "http://nohost/item/@@images/image/thumb.avif"
        )
        self.assertEqual(
            picture.img["src"], "http://nohost/item/@@images/image-128-abc.png"
        )

    def test_brain_tag_of_svg_or_custom_url_has_no_twin(self):
        view = NavigationRootScaling(self.item, self.request)
        for brain in (
            FakeBrain("http://nohost/item", content_type="image/svg+xml"),
            FakeBrain("http://nohost/item", download="https://cdn.example/x.png"),
        ):
            markup = view._tag_from_brain_image_scales(brain, "image", scale="thumb")
            self.assertTrue(markup.startswith("<img"), markup)


@unittest.skipUnless(avif_available(), "Pillow cannot encode AVIF")
class AvifUploadFallbackTests(unittest.TestCase):
    """An AVIF upload is offered as AVIF, with a JPEG fallback for browsers
    that cannot show AVIF."""

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def setUp(self):
        self.request = self.layer["request"]
        item = DummyContent()
        item.image = NamedImage(avif_bytes(), filename="pic.avif")
        self.layer["app"]._setOb("item", item)
        self.item = self.layer["app"].item
        self._orig_sizes = ImageScaling._sizes
        ImageScaling._sizes = SIZES
        self.images = ImageScaling(self.item, self.request)

    def tearDown(self):
        ImageScaling._sizes = self._orig_sizes

    def serve(self, url):
        self.request["TraversalRequestNameStack"] = []
        scale = self.images.publishTraverse(self.request, url.rsplit("/", 1)[-1])
        return scale.index_html()

    def picture(self, markup):
        picture = BeautifulSoup(markup, "html.parser").picture
        self.assertIsNotNone(picture, markup)
        return picture

    def assert_avif_with_jpeg_fallback(self, picture):
        avif = picture.find("source", type="image/avif")
        self.assertIsNotNone(avif, picture)
        self.assertIs(picture.find("source"), avif)  # first choice
        self.assertTrue(is_avif(self.serve(avif["srcset"].split()[0])))
        self.assertRegex(picture.img["src"], STABLE)
        self.assertTrue(is_jpeg(self.serve(picture.img["src"])))

    def test_upload_is_avif(self):
        self.assertEqual(self.item.image.contentType, "image/avif")

    def test_plain_scale_is_jpeg(self):
        scale = self.images.scale("image", "teaser")
        self.assertEqual(scale.mimetype, "image/jpeg")
        self.assertTrue(is_jpeg(scale.data.data))

    def test_plain_pre_scale_serves_jpeg(self):
        # Until generated, the URL carries the original's extension, as for
        # any format plone.scale re-encodes; the scale itself is the fallback.
        scale = self.images.scale("image", "preview", pre=True)
        self.assertRegex(scale.url, STABLE)
        self.assertTrue(is_jpeg(self.serve(scale.url)))

    def test_avif_scale_stays_avif(self):
        scale = self.images.scale("image", "teaser.avif")
        self.assertEqual(scale.mimetype, "image/avif")
        self.assertTrue(is_avif(scale.data.data))

    def test_tag_offers_avif_with_a_jpeg_img(self):
        markup = self.images.tag("image", scale="teaser")
        self.assert_avif_with_jpeg_fallback(self.picture(markup))

    def test_tag_of_the_original_offers_avif_with_a_jpeg_img(self):
        markup = self.images.tag("image")
        picture = self.picture(markup)
        self.assert_avif_with_jpeg_fallback(picture)
        self.assertEqual(picture.img["width"], "640")

    def test_high_pixel_density_srcset_is_jpeg(self):
        self.images.getHighPixelDensityScales = lambda: [{"scale": 2, "quality": 66}]
        markup = self.images.tag("image", scale="thumb")
        img = self.picture(markup).img
        url = img["srcset"].split()[0]
        self.assertRegex(url, STABLE)
        self.assertTrue(is_jpeg(self.serve(url)))

    def test_alpha_falls_back_to_png(self):
        self.item.image = NamedImage(avif_bytes("RGBA"), filename="pic.avif")
        picture = self.picture(self.images.tag("image", scale="teaser"))
        self.assertEqual(picture.source["type"], "image/avif")
        self.assertEqual(self.serve(picture.img["src"])[:4], b"\x89PNG")

    @mock.patch.object(plone.namedfile.picture, "get_allowed_scales", new=lambda: SIZES)
    @mock.patch.object(plone.namedfile.picture, "uuidToObject")
    def test_picture_variant_offers_avif_with_jpeg_sources(self, uuid_to_object):
        uuid_to_object.return_value = self.item
        tag = Img2PictureTag().create_picture_tag(
            [{"scale": "teaser", "additionalScales": ["preview"]}],
            {"src": "http://nohost/item/@@images/image/teaser"},
            uid="dummy_uuid",
            fieldname="image",
            resolve_urls=True,
        )
        avif, fallback = sources(tag)
        self.assertEqual(avif["type"], "image/avif")
        for candidate in fallback["srcset"].split(",\n"):
            self.assertRegex(candidate.split()[0], STABLE)
        self.assert_avif_with_jpeg_fallback(tag)

    def test_brain_tag_offers_avif(self):
        view = NavigationRootScaling(self.item, self.request)
        markup = view._tag_from_brain_image_scales(
            FakeBrain(
                "http://nohost/item",
                content_type="image/avif",
                download="@@images/image-128-abc.jpeg",
            ),
            "image",
            scale="thumb",
        )
        picture = self.picture(markup)
        self.assertEqual(
            picture.source["srcset"], "http://nohost/item/@@images/image/thumb.avif"
        )
        self.assertTrue(picture.img["src"].endswith(".jpeg"), picture.img["src"])

    def test_env_variable_off_keeps_the_jpeg_img(self):
        with mock.patch.dict(os.environ, {"NAMEDFILE_AVIF": "0"}):
            markup = self.images.tag("image", scale="teaser")
        img = BeautifulSoup(markup, "html.parser").img
        self.assertTrue(markup.startswith("<img"), markup)
        self.assertTrue(is_jpeg(self.serve(img["src"])))


@unittest.skipUnless(avif_available(), "Pillow cannot encode AVIF")
@mock.patch.object(
    plone.namedfile.picture,
    "get_allowed_scales",
    new=lambda: SIZES,
)
class AvifPictureTagTests(unittest.TestCase):
    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def setUp(self):
        item = DummyContent()
        item.image = NamedImage(getFile("image.png"), "image/png", "image.png")
        self.layer["app"]._setOb("item", item)
        self.item = self.layer["app"].item
        self._orig_sizes = ImageScaling._sizes
        ImageScaling._sizes = SIZES

    def tearDown(self):
        ImageScaling._sizes = self._orig_sizes

    def test_named_scale_sources_get_avif_twins_in_front(self):
        tag = Img2PictureTag().create_picture_tag(
            [
                {
                    "scale": "teaser",
                    "additionalScales": ["preview"],
                    "media": "(min-width: 768px)",
                }
            ],
            {"src": "/plone/pic/@@images/image/teaser", "alt": ""},
        )
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

    @mock.patch.object(plone.namedfile.picture, "uuidToObject")
    def test_resolved_sources_get_stable_avif_twins(self, uuid_to_object):
        uuid_to_object.return_value = self.item
        tag = Img2PictureTag().create_picture_tag(
            [{"scale": "teaser", "additionalScales": ["preview"]}],
            {"src": "http://nohost/item/@@images/image/teaser"},
            uid="dummy_uuid",
            fieldname="image",
            resolve_urls=True,
        )
        avif, original = sources(tag)
        for candidate in avif["srcset"].split(",\n"):
            url, width = candidate.split(" ")
            self.assertRegex(url, STABLE_AVIF)
        self.assertNotIn(".avif", original["srcset"])

    @mock.patch.object(plone.namedfile.picture, "uuidToObject")
    def test_svg_pictures_have_no_avif_twin(self, uuid_to_object):
        self.item.image = NamedImage(getFile("image.svg"), "image/svg+xml", "i.svg")
        uuid_to_object.return_value = self.item
        tag = Img2PictureTag().create_picture_tag(
            [{"scale": "teaser", "additionalScales": []}],
            {"src": "resolveuid/dummy_uuid/@@images/image/teaser"},
        )
        self.assertEqual(len(sources(tag)), 1)

    def test_urls_outside_images_get_no_twin(self):
        tag = Img2PictureTag().create_picture_tag(
            [{"scale": "teaser", "additionalScales": []}],
            {"src": "/plone/some-image.png"},
        )
        self.assertEqual(len(sources(tag)), 1)

    def test_env_variable_turns_twins_off(self):
        with mock.patch.dict(os.environ, {"NAMEDFILE_AVIF": "off"}):
            tag = Img2PictureTag().create_picture_tag(
                [{"scale": "teaser", "additionalScales": []}],
                {"src": "/plone/pic/@@images/image/teaser"},
            )
        self.assertEqual(len(sources(tag)), 1)
