from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.namedfile.brain_scaling import _title
from plone.namedfile.brain_scaling import BrainImageScaling
from plone.namedfile.scaling import ImageScaling
from plone.namedfile.testing import NAMEDFILE_PLONE_INTEGRATION
from plone.namedfile.tests.brain_images_helpers import assert_html_equal
from plone.namedfile.tests.brain_images_helpers import assert_scale_equal
from plone.namedfile.tests.brain_images_helpers import clear_scales
from plone.namedfile.tests.brain_images_helpers import counting_get_object_calls
from plone.namedfile.tests.brain_images_helpers import create_image
from plone.namedfile.tests.brain_images_helpers import create_multi_image_item
from plone.namedfile.tests.brain_images_helpers import create_multi_image_type
from plone.namedfile.tests.brain_images_helpers import FakeBrain
from plone.namedfile.tests.brain_images_helpers import first_image_entry
from plone.namedfile.tests.brain_images_helpers import get_brain
from plone.namedfile.tests.brain_images_helpers import image_entry
from plone.namedfile.tests.brain_images_helpers import multi_entry_image_scales
from plone.namedfile.tests.brain_images_helpers import scale_entry
from plone.namedfile.tests.brain_images_helpers import strict_get_object_calls
from plone.namedfile.tests.brain_images_helpers import wrapper_for
from types import SimpleNamespace
from unittest.mock import patch
from zExceptions import BadRequest
from zope.component import getMultiAdapter
from zope.publisher.interfaces import NotFound
from zope.traversing.interfaces import TraversalError

import unittest


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
