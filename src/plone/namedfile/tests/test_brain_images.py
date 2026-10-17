from DateTime import DateTime
from Missing import Value as MissingValue
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.base.interfaces import IImagingSchema
from plone.namedfile.brain_scaling import _title
from plone.namedfile.brain_scaling import BrainImageScale
from plone.namedfile.brain_scaling import BrainImageScaling
from plone.namedfile.scaling import ImageScale
from plone.namedfile.scaling import ImageScaling
from plone.namedfile.testing import NAMEDFILE_PLONE_INTEGRATION
from plone.namedfile.tests.brain_images_helpers import assert_html_equal
from plone.namedfile.tests.brain_images_helpers import assert_scale_equal
from plone.namedfile.tests.brain_images_helpers import clear_scales
from plone.namedfile.tests.brain_images_helpers import counting_get_object_calls
from plone.namedfile.tests.brain_images_helpers import create_image
from plone.namedfile.tests.brain_images_helpers import create_large_image
from plone.namedfile.tests.brain_images_helpers import create_multi_image_item
from plone.namedfile.tests.brain_images_helpers import create_multi_image_type
from plone.namedfile.tests.brain_images_helpers import FakeBrain
from plone.namedfile.tests.brain_images_helpers import first_image_entry
from plone.namedfile.tests.brain_images_helpers import get_brain
from plone.namedfile.tests.brain_images_helpers import image_entry
from plone.namedfile.tests.brain_images_helpers import malformed_image_scales
from plone.namedfile.tests.brain_images_helpers import missing_dimensions_image_scales
from plone.namedfile.tests.brain_images_helpers import multi_entry_image_scales
from plone.namedfile.tests.brain_images_helpers import scale_entry
from plone.namedfile.tests.brain_images_helpers import shadow_image_scales
from plone.namedfile.tests.brain_images_helpers import strict_get_object_calls
from plone.namedfile.tests.brain_images_helpers import wrapper_for
from plone.registry.interfaces import IRegistry
from types import SimpleNamespace
from unittest.mock import patch
from zExceptions import BadRequest
from zExceptions import Unauthorized
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.traversing.interfaces import TraversalError

import contextlib
import copy
import inspect
import unittest

RELATIVE_DOWNLOAD = "@@images/image-200-deadbeef.png"
SCALE_URL = f"http://nohost/plone/fake/{RELATIVE_DOWNLOAD}"


class DummyScale:
    def __init__(self, url, width, height, mimetype="image/png"):
        self.url = url
        self.width = width
        self.height = height
        self.mimetype = mimetype
        self.data = None

    def tag(self):
        return (
            f'<img src="{self.url}" width="{self.width}" ' f'height="{self.height}"/>'
        )


class BrainImagesInfrastructureTests(unittest.TestCase):
    """Smoke tests for the test layer, fixtures, and instrumentation."""

    layer = NAMEDFILE_PLONE_INTEGRATION

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def testLayerHasPloneSiteAndImageScalesColumn(self):
        self.assertTrue(self.portal)
        self.assertIn("image_scales", self.portal.portal_catalog._catalog.schema)

    def testCreateImageAndGetBrain(self):
        obj = create_image(self.portal, id="smoke_image")
        brain = get_brain(self.portal, obj)

        self.assertTrue(brain.getPath().endswith("/smoke_image"))
        self.assertIn("image", brain.image_scales)
        entry = first_image_entry(brain)
        self.assertEqual(entry["width"], 200)
        self.assertEqual(entry["height"], 200)
        self.assertEqual(entry["content-type"], "image/png")
        self.assertIn("scales", entry)

    def testInstrumentationPositiveControl(self):
        obj = create_image(self.portal, id="instrumented_image")
        brain = get_brain(self.portal, obj)

        with counting_get_object_calls() as calls:
            brain.getObject()
        self.assertEqual(len(calls), 1)

        with self.assertRaises(AssertionError):
            with strict_get_object_calls():
                brain.getObject()

    def testFakeBrainRecordsAccess(self):
        fake = FakeBrain(
            image_scales={
                "image": [
                    image_entry(
                        scales={
                            "thumb": scale_entry(
                                "@@images/image-128-deadbeef.png",
                                128,
                                128,
                            )
                        }
                    )
                ]
            }
        )

        _ = fake.getURL()
        _ = fake.Title
        _ = fake.UID
        _ = fake.modified

        self.assertTrue({"getURL", "Title", "UID", "modified"}.issubset(fake.accessed))

    def testContentlistingWrapper(self):
        fake = FakeBrain(image_scales={"image": [image_entry()]})
        wrapper = wrapper_for(fake)
        self.assertIs(wrapper.getDataOrigin(), fake)

    def testDomParityHelpers(self):
        assert_html_equal(
            self,
            '<img src="a" width="1" srcset="b 2x, a 1x"/>',
            '<img width="1" src="a" srcset="b 2x, a 1x"/>',
        )
        with self.assertRaises(AssertionError):
            assert_html_equal(
                self,
                '<img src="a" srcset="b 2x, a 1x"/>',
                '<img src="a" srcset="a 1x, b 2x"/>',
            )

    def testScaleComparatorIgnoresData(self):
        actual = DummyScale("http://nohost/item/@@images/thumb.png", 128, 128)
        expected = DummyScale("http://nohost/item/@@images/thumb.png", 128, 128)
        actual.data = b"bytes"

        assert_scale_equal(self, actual, expected)

    def testStaleMetadataHelperKeepsCatalogSnapshot(self):
        obj = create_image(self.portal, id="stale_image")
        brain = get_brain(self.portal, obj)
        old_download = first_image_entry(brain)["download"]

        clear_scales(obj)

        self.assertEqual(first_image_entry(brain)["download"], old_download)

    def testMultiImageTypeHelper(self):
        type_name = create_multi_image_type(self.portal)
        obj = create_multi_image_item(self.portal, type_name)

        brain = get_brain(self.portal, obj)
        self.assertEqual(sorted(brain.image_scales.keys()), ["image1", "image2"])


class BrainImageScalingRegistrationTests(unittest.TestCase):
    """Registration, context resolution, and field resolution."""

    layer = NAMEDFILE_PLONE_INTEGRATION

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.obj = create_image(self.portal)
        self.brain = get_brain(self.portal, self.obj)
        self.view = getMultiAdapter((self.brain, self.request), name="images")

    def testBrainViewResolves(self):
        self.assertIsInstance(self.view, BrainImageScaling)
        self.assertIs(self.view._metadata_origin(), self.brain)

    def testContentlistingWrapperResolves(self):
        wrapper = wrapper_for(self.brain)
        view = getMultiAdapter((wrapper, self.request), name="images")
        self.assertIsInstance(view, BrainImageScaling)
        self.assertIs(view._metadata_origin(), self.brain)
        self.assertTrue(view._supports_image_scales_metadata)

    def testRealObjectStillUsesImageScaling(self):
        view = getMultiAdapter((self.obj, self.request), name="images")
        self.assertIsInstance(view, ImageScaling)
        self.assertNotIsInstance(view, BrainImageScaling)

    def testRealContentlistingWrapperUsesObjectPath(self):
        wrapper = wrapper_for(self.obj)
        view = getMultiAdapter((wrapper, self.request), name="images")
        self.assertIsInstance(view, BrainImageScaling)
        self.assertIsNone(view._metadata_origin())

    def testWokenCatalogWrapperLosesMetadataOrigin(self):
        wrapper = wrapper_for(self.brain)
        wrapper.getObject()

        view = getMultiAdapter((wrapper, self.request), name="images")
        self.assertIsNone(view._metadata_origin())

    def testResolveMetadataSingleField(self):
        fieldname, entry = self.view._resolve_metadata()
        self.assertEqual(fieldname, "image")
        self.assertEqual(entry["width"], 200)

        explicit_name, explicit_entry = self.view._resolve_metadata("image")
        self.assertEqual(explicit_name, "image")
        self.assertIs(explicit_entry, entry)

    def testResolveMetadataMissingField(self):
        self.assertEqual(self.view._resolve_metadata("missing"), (None, None))

    def testResolveMetadataMultipleFields(self):
        type_name = create_multi_image_type(self.portal)
        obj = create_multi_image_item(self.portal, type_name)
        brain = get_brain(self.portal, obj)
        view = getMultiAdapter((brain, self.request), name="images")

        self.assertEqual(view._resolve_metadata(), (None, None))
        fieldname, entry = view._resolve_metadata("image1")
        self.assertEqual(fieldname, "image1")
        self.assertIn("download", entry)

    def testResolveMetadataNoMetadata(self):
        fake = FakeBrain()
        view = getMultiAdapter((fake, self.request), name="images")
        with self.assertLogs("plone.namedfile.brain_scaling", level="DEBUG"):
            self.assertEqual(view._resolve_metadata(), (None, None))

    def testResolveMetadataEmptyEntryList(self):
        fake = FakeBrain(image_scales={"image": []})
        view = getMultiAdapter((fake, self.request), name="images")
        self.assertEqual(view._resolve_metadata(), (None, None))
        self.assertEqual(view._resolve_metadata("image"), (None, None))

    def testResolveMetadataMultipleEntriesUsesFirst(self):
        fake = FakeBrain(image_scales=multi_entry_image_scales())
        view = getMultiAdapter((fake, self.request), name="images")

        with self.assertLogs(
            "plone.namedfile.brain_scaling",
            level="DEBUG",
        ) as captured:
            fieldname, entry = view._resolve_metadata("image")

        self.assertEqual(fieldname, "image")
        self.assertEqual(entry["download"], "@@images/image-200-deadbeef.png")
        self.assertIn("first of 2 entries", "\n".join(captured.output))

    def testSupportsImageScalesMetadata(self):
        self.assertTrue(self.view._supports_image_scales_metadata)

    def testSupportsImageScalesMetadataWithoutColumn(self):
        catalog = SimpleNamespace(_catalog=SimpleNamespace(schema=[]))
        with patch(
            "plone.namedfile.brain_scaling.getToolByName",
            return_value=catalog,
        ):
            view = getMultiAdapter((self.brain, self.request), name="images")
            self.assertFalse(view._supports_image_scales_metadata)

    def testTitleNormalization(self):
        self.assertEqual(_title(self.brain), "Image")
        self.assertEqual(_title(wrapper_for(self.brain)), "Image")
        self.assertEqual(_title(FakeBrain(title="Plain")), "Plain")
        self.assertEqual(_title(FakeBrain(title=lambda: "Callable")), "Callable")
        self.assertEqual(_title(FakeBrain(title="")), "")

    def testObjectViewDelegatesToRealObject(self):
        fake = FakeBrain(
            image_scales={"image": [image_entry()]},
            get_object=lambda: self.obj,
        )
        view = getMultiAdapter((fake, self.request), name="images")
        object_view = view._object_view(fake)

        self.assertIsInstance(object_view, ImageScaling)
        self.assertNotIsInstance(object_view, BrainImageScaling)

    def testTraversalIsRefused(self):
        with self.assertRaises(NotFound):
            self.view.publishTraverse(self.request, "image")
        with self.assertRaises(TraversalError):
            self.view.traverse("image", [])
        with self.assertRaises(BadRequest):
            self.view.browserDefault(self.request)


class BrainImageScaleTests(unittest.TestCase):
    """Metadata-backed scale object behavior."""

    layer = NAMEDFILE_PLONE_INTEGRATION

    def setUp(self):
        self.request = self.layer["request"]
        self.brain = FakeBrain(url="http://nohost/plone/fake")

    def make_scale(self, **kwargs):
        values = {
            "fieldname": "image",
            "download": RELATIVE_DOWNLOAD,
            "width": 200,
            "height": 200,
            "content_type": "image/png",
            "filename": "image.png",
        }
        values.update(kwargs)
        return BrainImageScale(self.brain, self.request, **values)

    def testConstructorAttributes(self):
        scale = self.make_scale(scale="thumb")

        self.assertEqual(scale.fieldname, "image")
        self.assertEqual(scale.scale, "thumb")
        self.assertEqual(scale.width, 200)
        self.assertEqual(scale.height, 200)
        self.assertEqual(scale.contentType, "image/png")
        self.assertEqual(scale.mimetype, "image/png")
        self.assertEqual(scale.filename, "image.png")
        self.assertIsNone(scale.data)
        self.assertFalse(hasattr(scale, "uid"))
        self.assertEqual(scale.srcset, [])
        self.assertEqual(scale.__name__, "image-thumb.png")
        self.assertEqual(scale.url, SCALE_URL)
        self.assertEqual(scale.absolute_url(), scale.url)

    def testOriginalName(self):
        self.assertEqual(self.make_scale().__name__, "image.png")

    def testSVGExtension(self):
        scale = self.make_scale(
            content_type="image/svg+xml",
            download="@@images/image-200.svg",
        )
        self.assertEqual(scale.__name__, "image.svg")

    def testExtensionFromDownload(self):
        scale = self.make_scale(
            content_type=None,
            download="@@images/image-200.jpg?version=1",
        )
        self.assertEqual(scale.__name__, "image.jpg")

    def testRelativeURLJoinsOrigin(self):
        brain = FakeBrain(url="http://nohost/plone/fake/")
        scale = BrainImageScale(
            brain,
            self.request,
            fieldname="image",
            download=RELATIVE_DOWNLOAD,
            width=200,
            height=200,
            content_type="image/png",
        )
        self.assertEqual(scale.url, SCALE_URL)

    def testAbsoluteAndRootRelativeURLsPassThrough(self):
        absolute = self.make_scale(download="https://cdn.example.com/image.png")
        root_relative = self.make_scale(download="/static/image.png")

        self.assertEqual(absolute.url, "https://cdn.example.com/image.png")
        self.assertEqual(root_relative.url, "/static/image.png")

    def testURLPreservesQueryAndFragment(self):
        scale = self.make_scale(
            download="@@images/image-200-deadbeef.png?v=1#frag",
        )
        self.assertEqual(scale.url, f"{SCALE_URL}?v=1#frag")

    def testTagDefaultsMatchImageScale(self):
        scale = self.make_scale()
        self.assertEqual(scale.srcset_attribute(), "")
        assert_html_equal(
            self,
            scale.tag(),
            (
                f'<img src="{SCALE_URL}" alt="Fake" title="Fake" '
                'height="200" width="200"/>'
            ),
        )

    def testTagMatchesObjectImageScale(self):
        class DummyImage:
            contentType = "image/png"
            _width = 200
            _height = 200

        class DummyContext:
            def absolute_url(self):
                return "http://nohost/plone/fake"

            def Title(self):
                return "Fake"

        object_scale = ImageScale(
            DummyContext(),
            self.request,
            data=DummyImage(),
            fieldname="image",
            uid="image-200-deadbeef",
        )

        assert_html_equal(self, self.make_scale().tag(), object_scale.tag())

    def testTagOverridesAndExtraAttributes(self):
        scale = self.make_scale()
        html = scale.tag(
            alt="Alt",
            title="Title",
            css_class="thumb",
            width=100,
            height=50,
            loading="lazy",
        )
        assert_html_equal(
            self,
            html,
            (
                f'<img src="{SCALE_URL}" alt="Alt" title="Title" '
                'height="50" width="100" class="thumb" loading="lazy"/>'
            ),
        )

    def testTagWithoutDimensionsOmitsThem(self):
        scale = self.make_scale(width=None, height=None)
        html = scale.tag()
        self.assertNotIn("width=", html)
        self.assertNotIn("height=", html)

    def make_scale_with_title(self, title):
        brain = FakeBrain(url="http://nohost/plone/fake", title=title)
        return BrainImageScale(
            brain,
            self.request,
            fieldname="image",
            download="/static/image.png",
            width=200,
            height=200,
            content_type="image/png",
        )

    def testTitleNormalization(self):
        self.assertEqual(self.make_scale().title, "Fake")
        self.assertEqual(
            self.make_scale_with_title(lambda: "Callable").title,
            "Callable",
        )
        self.assertEqual(self.make_scale_with_title("").title, "")

    def testValidateAccessIsNoop(self):
        self.assertIsNone(self.make_scale().validate_access())

    def testDataServingIsRefused(self):
        scale = self.make_scale()
        with self.assertRaises(NotFound):
            scale.index_html()
        with self.assertRaises(NotFound):
            scale.HEAD(self.request)
        with self.assertRaises(NotFound):
            scale.set_headers()


class BrainImageScalingBehaviorTests(unittest.TestCase):
    """Metadata-first behavior, accessors, and object fallback."""

    layer = NAMEDFILE_PLONE_INTEGRATION

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.obj = create_image(self.portal)
        self.brain = get_brain(self.portal, self.obj)
        self.object_view = getMultiAdapter((self.obj, self.request), name="images")
        self.brain_view = getMultiAdapter((self.brain, self.request), name="images")
        self.disable_hidpi(self.object_view)
        self.disable_hidpi(self.brain_view)

    @staticmethod
    def disable_hidpi(view):
        view.getHighPixelDensityScales = lambda: []

    def make_no_image_view(self):
        content_id = f"no_image_{self.brain.UID}"
        self.portal.invokeFactory("News Item", content_id, title="No Image")
        obj = self.portal[content_id]
        obj.reindexObject()
        brain = get_brain(self.portal, obj)
        return getMultiAdapter((brain, self.request), name="images")

    def testTagNamedScaleParityAndNoWake(self):
        with strict_get_object_calls():
            brain_tag = self.brain_view.tag("image", scale="thumb")
        object_tag = self.object_view.tag("image", scale="thumb")
        assert_html_equal(self, brain_tag, object_tag)

    def testTagOriginalParity(self):
        brain_tag = self.brain_view.tag("image")
        object_tag = self.object_view.tag("image", width=200, height=200)
        assert_html_equal(self, brain_tag, object_tag)

    def testOriginalMetadataUsesIndexedURL(self):
        scale = self.brain_view.scale("image")
        self.assertIn("image-200-", scale.url)

    def testTagConsumesIncludeSrcset(self):
        html = self.brain_view.tag(
            "image",
            scale="thumb",
            include_srcset=False,
            loading="lazy",
        )
        self.assertNotIn("include_srcset", html)
        self.assertIn('loading="lazy"', html)

    def testWrapperTagParity(self):
        wrapper = wrapper_for(self.brain)
        wrapper_view = getMultiAdapter((wrapper, self.request), name="images")
        self.disable_hidpi(wrapper_view)
        with strict_get_object_calls():
            wrapper_tag = wrapper_view.tag("image", scale="thumb")
        object_tag = self.object_view.tag("image", scale="thumb")
        assert_html_equal(self, wrapper_tag, object_tag)

    def testScaleNamedParity(self):
        brain_scale = self.brain_view.scale("image", scale="thumb")
        object_scale = self.object_view.scale("image", scale="thumb")

        self.assertIsInstance(brain_scale, BrainImageScale)
        assert_scale_equal(self, brain_scale, object_scale)

    def testScaleOriginalParity(self):
        brain_scale = self.brain_view.scale("image")
        object_scale = self.object_view.scale("image", width=200, height=200)
        self.assertIsInstance(brain_scale, BrainImageScale)
        assert_scale_equal(self, brain_scale, object_scale)

    def testScaleExplicitDimensionsMatchMetadata(self):
        brain_scale = self.brain_view.scale("image", width=128, height=128)
        object_scale = self.object_view.scale("image", width=128, height=128)

        self.assertIsInstance(brain_scale, BrainImageScale)
        assert_scale_equal(self, brain_scale, object_scale)

    def testMissingConfiguredScaleFallsBack(self):
        with self.assertLogs(
            "plone.namedfile.brain_scaling",
            level="DEBUG",
        ) as captured:
            with counting_get_object_calls() as calls:
                scale = self.brain_view.scale("image", scale="huge")

        self.assertIsNotNone(scale)
        self.assertNotIsInstance(scale, BrainImageScale)
        self.assertEqual(len(calls), 1)
        self.assertIn("falling back", "\n".join(captured.output))

    def testScaleWithDimensionsTakesNamedScale(self):
        with self.assertLogs(
            "plone.namedfile.brain_scaling",
            level="WARNING",
        ):
            with strict_get_object_calls():
                scale = self.brain_view.scale(
                    "image",
                    scale="thumb",
                    width=999,
                    height=999,
                )

        self.assertIsInstance(scale, BrainImageScale)
        self.assertEqual(scale.__name__, "image-thumb.png")

    def testPreScaleUsesMetadataWithoutWake(self):
        with strict_get_object_calls():
            scale = self.brain_view.scale("image", scale="thumb", pre=True)
        self.assertIsInstance(scale, BrainImageScale)

    def testUnknownScaleWithCropReturnsNoneWithoutWake(self):
        with strict_get_object_calls():
            self.assertIsNone(self.brain_view.scale("image", scale="nope", mode="crop"))

    def testUnknownScaleNameReturnsNoneWithoutWake(self):
        with strict_get_object_calls():
            self.assertIsNone(self.brain_view.scale("image", scale="nope"))

    def testCropModeFallsBack(self):
        with counting_get_object_calls() as calls:
            scale = self.brain_view.scale("image", scale="thumb", mode="crop")

        self.assertNotIsInstance(scale, BrainImageScale)
        self.assertEqual(len(calls), 1)

    def testArbitraryDimensionsFallBack(self):
        with counting_get_object_calls() as calls:
            scale = self.brain_view.scale("image", width=77)

        self.assertNotIsInstance(scale, BrainImageScale)
        self.assertEqual(len(calls), 1)

    def testMissingFieldReturnsNoneWithoutWake(self):
        with strict_get_object_calls():
            self.assertIsNone(self.brain_view.scale("missing"))

    def testNoImageReturnsEmptyWithoutWake(self):
        view = self.make_no_image_view()
        with strict_get_object_calls():
            self.assertIsNone(view.scale("image"))
            self.assertIsNone(view.tag("image"))
            self.assertEqual(view.getImageSize("image"), (0, 0))

    def testSchemaWithoutColumnFallsBack(self):
        catalog = SimpleNamespace(_catalog=SimpleNamespace(schema=[]))
        with patch(
            "plone.namedfile.brain_scaling.getToolByName",
            return_value=catalog,
        ):
            view = getMultiAdapter((self.brain, self.request), name="images")
            view.getHighPixelDensityScales = lambda: []
            with counting_get_object_calls() as calls:
                html = view.tag("image", scale="thumb")

        self.assertIsNotNone(html)
        self.assertEqual(len(calls), 1)

    def testMalformedMetadataFallsBack(self):
        with shadow_image_scales(self.brain, malformed_image_scales()):
            with counting_get_object_calls() as calls:
                html = self.brain_view.tag("image")

        self.assertIsNotNone(html)
        self.assertEqual(len(calls), 1)

    def testGetImageSizeUsesMetadataWithoutWake(self):
        with strict_get_object_calls():
            self.assertEqual(self.brain_view.getImageSize("image"), (200, 200))

    def testGetImageSizeMissingDimensionsFallsBack(self):
        with shadow_image_scales(
            self.brain,
            missing_dimensions_image_scales(),
        ):
            with counting_get_object_calls() as calls:
                size = self.brain_view.getImageSize("image")

        self.assertEqual(size, (200, 200))
        self.assertEqual(len(calls), 1)

    def testModifiedUsesBrainValueWithoutWake(self):
        with strict_get_object_calls():
            modified = self.brain_view.modified("image")
        self.assertEqual(modified, DateTime(self.brain.modified).millis())

    def testUnauthorizedFallbackPropagates(self):
        fake = FakeBrain(
            image_scales={"image": [image_entry()]},
            get_object=lambda: (_ for _ in ()).throw(Unauthorized("nope")),
        )
        view = getMultiAdapter((fake, self.request), name="images")
        with self.assertRaises(Unauthorized):
            view.scale("image", width=77)

    def testGetObjectNoneYieldsEmptyResults(self):
        fake = FakeBrain(
            image_scales=missing_dimensions_image_scales(),
            get_object=lambda: None,
        )
        view = getMultiAdapter((fake, self.request), name="images")

        self.assertIsNone(view.scale("image", width=77))
        self.assertEqual(view.getImageSize("image"), (0, 0))

    def testWrongTypedMetadataFallsBack(self):
        bad_metadata = {"image": [image_entry(width="abc", height=200)]}
        with shadow_image_scales(self.brain, bad_metadata):
            with counting_get_object_calls() as calls:
                html = self.brain_view.tag("image")

        self.assertIsNotNone(html)
        self.assertEqual(len(calls), 1)

    def testUnauthorizedGetImageSizePropagates(self):
        fake = FakeBrain(
            image_scales=missing_dimensions_image_scales(),
            get_object=lambda: (_ for _ in ()).throw(Unauthorized("nope")),
        )
        view = getMultiAdapter((fake, self.request), name="images")
        with self.assertRaises(Unauthorized):
            view.getImageSize("image")

    def testModifiedMissingValueReturnsZero(self):
        class MissingModifiedBrain(FakeBrain):
            @property
            def modified(self):
                return MissingValue

        fake = MissingModifiedBrain(image_scales={"image": [image_entry()]})
        view = getMultiAdapter((fake, self.request), name="images")
        self.assertEqual(view.modified("image"), 0)


class BrainImageScalingSrcsetTests(unittest.TestCase):
    """Metadata-first srcset behavior and its documented divergence."""

    layer = NAMEDFILE_PLONE_INTEGRATION

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.obj = create_large_image(self.portal)
        self.brain = get_brain(self.portal, self.obj)
        self.object_view = getMultiAdapter((self.obj, self.request), name="images")
        self.brain_view = getMultiAdapter((self.brain, self.request), name="images")

    def metadata_without_scale(self, name, fieldname="image"):
        entry = copy.deepcopy(first_image_entry(self.brain, fieldname))
        entry["scales"].pop(name)
        return {fieldname: [entry]}

    def assert_fell_back_to_object(self, calls):
        self.assertEqual(len(calls), 1)

    def make_no_image_view(self):
        content_id = f"no_image_srcset_{self.brain.UID}"
        self.portal.invokeFactory("News Item", content_id, title="No Image")
        obj = self.portal[content_id]
        obj.reindexObject()
        brain = get_brain(self.portal, obj)
        return getMultiAdapter((brain, self.request), name="images")

    def testSrcsetParityWithoutWake(self):
        with strict_get_object_calls():
            brain_srcset = self.brain_view.srcset("image", scale_in_src="large")
        object_srcset = self.object_view.srcset("image", scale_in_src="large")
        assert_html_equal(self, brain_srcset, object_srcset)

    def testSrcsetOriginalIncluded(self):
        srcset = self.brain_view.srcset("image", scale_in_src="large")
        self.assertIn("900w", srcset)
        self.assertIn("/image-900-", srcset)

    def testSrcsetSmallImageParityWithoutWake(self):
        obj = create_image(self.portal)
        brain = get_brain(self.portal, obj)
        brain_view = getMultiAdapter((brain, self.request), name="images")
        object_view = getMultiAdapter((obj, self.request), name="images")

        with strict_get_object_calls():
            brain_srcset = brain_view.srcset("image", scale_in_src="mini")
        object_srcset = object_view.srcset("image", scale_in_src="mini")
        assert_html_equal(self, brain_srcset, object_srcset)
        self.assertEqual(brain_srcset.count("200w"), 1)

    def testSrcsetAttributes(self):
        with strict_get_object_calls():
            brain_srcset = self.brain_view.srcset(
                "image",
                scale_in_src="large",
                sizes="50vw",
                alt="Alt",
                title="Title",
                css_class="foo",
                loading="lazy",
            )
        object_srcset = self.object_view.srcset(
            "image",
            scale_in_src="large",
            sizes="50vw",
            alt="Alt",
            title="Title",
            css_class="foo",
            loading="lazy",
        )
        assert_html_equal(self, brain_srcset, object_srcset)

    def testSrcsetKeepsCallerDimensions(self):
        with strict_get_object_calls():
            brain_srcset = self.brain_view.srcset(
                "image",
                scale_in_src="large",
                width=123,
                height=45,
            )
        object_srcset = self.object_view.srcset(
            "image",
            scale_in_src="large",
            width=123,
            height=45,
        )
        assert_html_equal(self, brain_srcset, object_srcset)
        self.assertIn('width="123"', brain_srcset)
        self.assertIn('height="45"', brain_srcset)

    def testSrcsetFalsyTitleOmitsTitle(self):
        with strict_get_object_calls():
            brain_srcset = self.brain_view.srcset(
                "image",
                scale_in_src="large",
                title="",
            )
        object_srcset = self.object_view.srcset(
            "image",
            scale_in_src="large",
            title="",
        )
        assert_html_equal(self, brain_srcset, object_srcset)
        self.assertNotIn("title=", brain_srcset)

    def testSrcsetSkipsMissingScale(self):
        with shadow_image_scales(
            self.brain,
            self.metadata_without_scale("teaser"),
        ):
            with self.assertLogs(
                "plone.namedfile.brain_scaling",
                level="DEBUG",
            ) as captured:
                with strict_get_object_calls():
                    brain_srcset = self.brain_view.srcset(
                        "image",
                        scale_in_src="large",
                    )
        object_srcset = self.object_view.srcset("image", scale_in_src="large")

        self.assertNotIn("600w", brain_srcset)
        self.assertIn("600w", object_srcset)
        self.assertLess(len(brain_srcset), len(object_srcset))
        self.assertIn("skips missing scale", "\n".join(captured.output))

    def testSrcsetSelectedScaleMissingFallsBack(self):
        with shadow_image_scales(
            self.brain,
            self.metadata_without_scale("large"),
        ):
            with counting_get_object_calls() as calls:
                brain_srcset = self.brain_view.srcset(
                    "image",
                    scale_in_src="large",
                )

        self.assertIsNotNone(brain_srcset)
        self.assert_fell_back_to_object(calls)
        assert_html_equal(
            self,
            brain_srcset,
            self.object_view.srcset("image", scale_in_src="large"),
        )

    def testSrcsetDefaultHugeFallsBack(self):
        with counting_get_object_calls() as calls:
            brain_srcset = self.brain_view.srcset("image")

        self.assertIsNotNone(brain_srcset)
        self.assert_fell_back_to_object(calls)
        assert_html_equal(
            self,
            brain_srcset,
            self.object_view.srcset("image"),
        )

    def testSrcsetUnknownScaleInSrcUsesFirstAvailable(self):
        with strict_get_object_calls():
            brain_srcset = self.brain_view.srcset("image", scale_in_src="nope")
        object_srcset = self.object_view.srcset("image", scale_in_src="nope")
        assert_html_equal(self, brain_srcset, object_srcset)

    def testSrcsetNoImageReturnsNone(self):
        view = self.make_no_image_view()
        with strict_get_object_calls():
            self.assertIsNone(view.srcset("image"))

    def testSrcsetSchemaWithoutColumnFallsBack(self):
        catalog = SimpleNamespace(_catalog=SimpleNamespace(schema=[]))
        with patch(
            "plone.namedfile.brain_scaling.getToolByName",
            return_value=catalog,
        ):
            view = getMultiAdapter((self.brain, self.request), name="images")
            with counting_get_object_calls() as calls:
                srcset = view.srcset("image", scale_in_src="large")

        self.assertIsNotNone(srcset)
        self.assert_fell_back_to_object(calls)

    def testSrcsetMalformedMetadataFallsBack(self):
        malformed = {
            "image": [
                image_entry(
                    download=None,
                    width=900,
                    height=900,
                )
            ]
        }
        with shadow_image_scales(self.brain, malformed):
            with counting_get_object_calls() as calls:
                srcset = self.brain_view.srcset("image", scale_in_src="large")

        self.assertIsNotNone(srcset)
        self.assert_fell_back_to_object(calls)

    def testSrcsetMalformedNestedScaleFallsBack(self):
        entry = copy.deepcopy(first_image_entry(self.brain))
        entry["scales"]["teaser"] = {
            "download": None,
            "width": 600,
            "height": 600,
        }
        with shadow_image_scales(self.brain, {"image": [entry]}):
            with counting_get_object_calls() as calls:
                srcset = self.brain_view.srcset("image", scale_in_src="large")

        self.assertIsNotNone(srcset)
        self.assert_fell_back_to_object(calls)
        assert_html_equal(
            self,
            srcset,
            self.object_view.srcset("image", scale_in_src="large"),
        )

    def testSrcsetZeroDimensionsFallsBack(self):
        zero = {
            "image": [
                image_entry(
                    download="@@images/image-0-deadbeef.png",
                    width=0,
                    height=0,
                )
            ]
        }
        with shadow_image_scales(self.brain, zero):
            with counting_get_object_calls() as calls:
                srcset = self.brain_view.srcset("image", scale_in_src="large")

        self.assertIsNotNone(srcset)
        self.assert_fell_back_to_object(calls)

    def testSrcsetWrapperParity(self):
        wrapper = wrapper_for(self.brain)
        wrapper_view = getMultiAdapter((wrapper, self.request), name="images")

        with strict_get_object_calls():
            wrapper_srcset = wrapper_view.srcset("image", scale_in_src="large")
        object_srcset = self.object_view.srcset("image", scale_in_src="large")
        assert_html_equal(self, wrapper_srcset, object_srcset)


PICTURE_VARIANTS = {
    "test": {
        "title": "Test",
        "sourceset": [
            {
                "scale": "large",
                "additionalScales": ["preview", "teaser"],
                "sizes": "50vw",
                "media": "(min-width: 800px)",
            }
        ],
    },
    "no_additional": {
        "title": "No additional scales",
        "sourceset": [{"scale": "large"}],
    },
    "empty_variant": {},
    "empty": {
        "title": "Empty",
        "sourceset": [],
    },
    "missing_scale": {
        "title": "Missing",
        "sourceset": [
            {
                "scale": "great",
                "additionalScales": ["large"],
            }
        ],
    },
    "unknown_scale": {
        "title": "Unknown scale",
        "sourceset": [
            {
                "scale": "large",
                "additionalScales": ["notallowed"],
            }
        ],
    },
}

ALLOWED_SCALES = {
    "large": (800, 65536),
    "teaser": (600, 65536),
    "preview": (400, 65536),
    "great": (1200, 65536),
}

SMALL_ALLOWED_SCALES = {
    "large": (800, 65536),
    "teaser": (600, 65536),
    "preview": (400, 65536),
}


class BrainImageScalingPictureTests(unittest.TestCase):
    """Metadata-first picture() behavior and the resolver hook."""

    layer = NAMEDFILE_PLONE_INTEGRATION

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.obj = create_large_image(self.portal)
        self.brain = get_brain(self.portal, self.obj)
        self.object_view = getMultiAdapter((self.obj, self.request), name="images")
        self.brain_view = getMultiAdapter((self.brain, self.request), name="images")
        self.object_view.getHighPixelDensityScales = lambda: []
        self.brain_view.getHighPixelDensityScales = lambda: []

        for target in (
            "plone.namedfile.picture.get_picture_variants",
            "plone.namedfile.scaling.get_picture_variants",
        ):
            patcher = patch(target, return_value=PICTURE_VARIANTS)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch(
            "plone.namedfile.picture.get_allowed_scales",
            return_value=ALLOWED_SCALES,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def picture_without_uuid(self, view, **kwargs):
        with patch(
            "plone.namedfile.picture.uuidToObject",
            side_effect=AssertionError("uuidToObject called"),
        ):
            with strict_get_object_calls():
                return view.picture("image", **kwargs)

    def object_picture(self, **kwargs):
        with patch(
            "plone.namedfile.picture.uuidToObject",
            return_value=self.obj,
        ):
            return self.object_view.picture("image", **kwargs)

    def make_no_image_view(self):
        content_id = f"no_image_picture_{self.brain.UID}"
        self.portal.invokeFactory("News Item", content_id, title="No Image")
        obj = self.portal[content_id]
        obj.reindexObject()
        brain = get_brain(self.portal, obj)
        return getMultiAdapter((brain, self.request), name="images")

    def testPictureParityWithoutWake(self):
        brain_picture = self.picture_without_uuid(
            self.brain_view,
            picture_variant="test",
        )
        object_picture = self.object_picture(picture_variant="test")
        assert_html_equal(self, brain_picture, object_picture)

    def testPictureAttributes(self):
        brain_picture = self.picture_without_uuid(
            self.brain_view,
            picture_variant="test",
            alt="Alt",
            css_class="captioned",
            title="Title",
            lazy=False,
        )
        object_picture = self.object_picture(
            picture_variant="test",
            alt="Alt",
            css_class="captioned",
            title="Title",
            lazy=False,
        )
        assert_html_equal(self, brain_picture, object_picture)
        self.assertIn('class="captioned"', brain_picture)
        self.assertNotIn('loading="lazy"', brain_picture)
        self.assertIn('alt="Alt"', brain_picture)
        self.assertIn('sizes="50vw"', brain_picture)
        self.assertIn('media="(min-width: 800px)"', brain_picture)

    def testPictureAdditionalScalesOmitted(self):
        with patch(
            "plone.namedfile.picture.get_allowed_scales",
            return_value=SMALL_ALLOWED_SCALES,
        ):
            brain_picture = self.picture_without_uuid(
                self.brain_view,
                picture_variant="no_additional",
            )
            object_picture = self.object_picture(
                picture_variant="no_additional",
            )
        assert_html_equal(self, brain_picture, object_picture)

    def testPictureUnknownVariantFallsBackToTag(self):
        brain_picture = self.picture_without_uuid(
            self.brain_view,
            picture_variant="unknown",
        )
        assert_html_equal(
            self,
            brain_picture,
            self.brain_view.tag("image", alt=None),
        )
        self.assertTrue(brain_picture.startswith("<img"))

    def testPictureEmptySourcesetReturnsNone(self):
        self.assertIsNone(
            self.picture_without_uuid(
                self.brain_view,
                picture_variant="empty",
            )
        )
        self.assertIsNone(
            self.picture_without_uuid(
                self.brain_view,
                picture_variant="empty_variant",
            )
        )

    def testPictureUnknownAdditionalScaleDoesNotFallBack(self):
        picture = self.picture_without_uuid(
            self.brain_view,
            picture_variant="unknown_scale",
        )
        self.assertIsNotNone(picture)
        self.assertIn("<picture", picture)

    def testPictureMissingScaleFallsBack(self):
        with patch(
            "plone.namedfile.picture.uuidToObject",
            return_value=self.obj,
        ):
            with counting_get_object_calls() as calls:
                brain_picture = self.brain_view.picture(
                    "image",
                    picture_variant="missing_scale",
                )
            object_picture = self.object_view.picture(
                "image",
                picture_variant="missing_scale",
            )

        self.assertIsNotNone(brain_picture)
        self.assertEqual(len(calls), 1)
        assert_html_equal(self, brain_picture, object_picture)

    def testPictureNoImageReturnsNone(self):
        view = self.make_no_image_view()
        with strict_get_object_calls():
            self.assertIsNone(view.picture("image", picture_variant="test"))
            self.assertIsNone(view.picture("image", picture_variant="unknown"))

    def testPictureUnauthorizedFallbackPropagates(self):
        fake = FakeBrain(
            image_scales={"image": [image_entry()]},
            get_object=lambda: (_ for _ in ()).throw(Unauthorized("nope")),
        )
        view = getMultiAdapter((fake, self.request), name="images")
        with self.assertRaises(Unauthorized):
            view.picture("image", picture_variant="missing_scale")

    def testPictureMalformedNestedScaleFallsBack(self):
        entry = copy.deepcopy(first_image_entry(self.brain))
        entry["scales"]["teaser"] = {
            "download": None,
            "width": 600,
            "height": 600,
        }
        with patch(
            "plone.namedfile.picture.uuidToObject",
            return_value=self.obj,
        ):
            with shadow_image_scales(self.brain, {"image": [entry]}):
                with counting_get_object_calls() as calls:
                    picture = self.brain_view.picture(
                        "image",
                        picture_variant="test",
                    )

        self.assertIsNotNone(picture)
        self.assertEqual(len(calls), 1)

    def testPictureSchemaWithoutColumnFallsBack(self):
        catalog = SimpleNamespace(_catalog=SimpleNamespace(schema=[]))
        with patch(
            "plone.namedfile.brain_scaling.getToolByName",
            return_value=catalog,
        ):
            view = getMultiAdapter((self.brain, self.request), name="images")
            with patch(
                "plone.namedfile.picture.uuidToObject",
                return_value=self.obj,
            ):
                with counting_get_object_calls() as calls:
                    picture = view.picture("image", picture_variant="test")

        self.assertIsNotNone(picture)
        self.assertEqual(len(calls), 1)

    def testPictureMalformedMetadataFallsBack(self):
        with patch(
            "plone.namedfile.picture.uuidToObject",
            return_value=self.obj,
        ):
            with shadow_image_scales(self.brain, malformed_image_scales()):
                with counting_get_object_calls() as calls:
                    picture = self.brain_view.picture(
                        "image",
                        picture_variant="test",
                    )

        self.assertIsNotNone(picture)
        self.assertEqual(len(calls), 1)

    def testPictureWrapperParity(self):
        wrapper = wrapper_for(self.brain)
        wrapper_view = getMultiAdapter((wrapper, self.request), name="images")

        wrapper_picture = self.picture_without_uuid(
            wrapper_view,
            picture_variant="test",
        )
        object_picture = self.object_picture(picture_variant="test")
        assert_html_equal(self, wrapper_picture, object_picture)


class BrainImageScalingHiDPITests(unittest.TestCase):
    """HiDPI is metadata-free and requires an explicit object fallback."""

    layer = NAMEDFILE_PLONE_INTEGRATION
    hidpi_scales = [{"scale": 2, "quality": 66}]

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.obj = create_image(self.portal)
        self.brain = get_brain(self.portal, self.obj)
        self.object_view = getMultiAdapter((self.obj, self.request), name="images")
        self.brain_view = getMultiAdapter((self.brain, self.request), name="images")

    def use_hidpi(self, view=None):
        (view or self.brain_view).getHighPixelDensityScales = lambda: self.hidpi_scales

    def use_no_hidpi(self, view=None):
        (view or self.brain_view).getHighPixelDensityScales = lambda: []

    @contextlib.contextmanager
    def hidpi_configured(self):
        with patch.object(
            ImageScaling,
            "getHighPixelDensityScales",
            return_value=self.hidpi_scales,
        ):
            yield

    def make_no_image_view(self):
        content_id = f"no_image_hidpi_{self.brain.UID}"
        self.portal.invokeFactory("News Item", content_id, title="No Image")
        obj = self.portal[content_id]
        obj.reindexObject()
        brain = get_brain(self.portal, obj)
        return getMultiAdapter((brain, self.request), name="images")

    def testDefaultOmitsHiDPIWithoutWake(self):
        self.use_hidpi()
        with strict_get_object_calls():
            html = self.brain_view.tag("image", scale="icon")
        self.assertNotIn("srcset=", html)

    def testIncludeSrcsetFalseOmitsHiDPIWithoutWake(self):
        self.use_hidpi()
        with strict_get_object_calls():
            html = self.brain_view.tag(
                "image",
                scale="icon",
                include_srcset=False,
            )
        self.assertNotIn("srcset=", html)

    def testPreTrueDefaultOmitsHiDPIWithoutWake(self):
        self.use_hidpi()
        with strict_get_object_calls():
            scale = self.brain_view.scale("image", scale="icon", pre=True)
        self.assertIsInstance(scale, BrainImageScale)
        self.assertEqual(scale.srcset, [])

    def testIncludeSrcsetTrueWithoutHiDPIStaysMetadata(self):
        self.use_no_hidpi()
        with strict_get_object_calls():
            scale = self.brain_view.scale(
                "image",
                scale="icon",
                include_srcset=True,
            )
        self.assertIsInstance(scale, BrainImageScale)
        self.assertEqual(scale.srcset, [])

    def testIncludeSrcsetTrueWithHiDPIFallsBackForScale(self):
        with self.hidpi_configured():
            with counting_get_object_calls() as calls:
                scale = self.brain_view.scale(
                    "image",
                    scale="icon",
                    include_srcset=True,
                )

        self.assertNotIsInstance(scale, BrainImageScale)
        self.assertTrue(scale.srcset)
        self.assertEqual(len(calls), 1)

    def testIncludeSrcsetTrueWithHiDPIFallsBackForTag(self):
        with self.hidpi_configured():
            with counting_get_object_calls() as calls:
                brain_tag = self.brain_view.tag(
                    "image",
                    scale="icon",
                    include_srcset=True,
                )
            object_tag = self.object_view.tag("image", scale="icon")

        self.assertIn("srcset=", brain_tag)
        self.assertIn(" 2x", brain_tag)
        self.assertNotIn("include_srcset", brain_tag)
        assert_html_equal(self, brain_tag, object_tag)
        self.assertEqual(len(calls), 1)

    def testUnknownScaleWithHiDPIStillReturnsNoneWithoutWake(self):
        self.use_hidpi()
        with strict_get_object_calls():
            self.assertIsNone(
                self.brain_view.scale(
                    "image",
                    scale="nope",
                    include_srcset=True,
                )
            )

    def testNoImageWithHiDPIReturnsNoneWithoutWake(self):
        view = self.make_no_image_view()
        self.use_hidpi(view)
        with strict_get_object_calls():
            self.assertIsNone(view.tag("image", include_srcset=True))

    def testDefaultFallbackDoesNotReenableHiDPI(self):
        with self.hidpi_configured():
            with counting_get_object_calls() as calls:
                html = self.brain_view.tag("image", scale="huge")

        self.assertNotIn("srcset=", html)
        self.assertEqual(len(calls), 1)

    def testRegistryHiDPIEnablesFallback(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IImagingSchema, prefix="plone")
        old_scales = settings.highpixeldensity_scales
        old_quality = settings.quality_2x
        settings.highpixeldensity_scales = "2x"
        settings.quality_2x = 66
        self.addCleanup(
            setattr,
            settings,
            "highpixeldensity_scales",
            old_scales,
        )
        self.addCleanup(setattr, settings, "quality_2x", old_quality)

        with counting_get_object_calls() as calls:
            scale = self.brain_view.scale(
                "image",
                scale="icon",
                include_srcset=True,
            )

        self.assertNotIsInstance(scale, BrainImageScale)
        self.assertTrue(scale.srcset)
        self.assertEqual(len(calls), 1)

    def testSrcsetAndPictureHaveNoIncludeSrcsetParameter(self):
        self.assertNotIn(
            "include_srcset",
            inspect.signature(self.brain_view.srcset).parameters,
        )
        self.assertNotIn(
            "include_srcset",
            inspect.signature(self.brain_view.picture).parameters,
        )
