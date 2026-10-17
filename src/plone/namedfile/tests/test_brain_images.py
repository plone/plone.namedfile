from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
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
from plone.namedfile.tests.brain_images_helpers import scale_entry
from plone.namedfile.tests.brain_images_helpers import strict_get_object_calls
from plone.namedfile.tests.brain_images_helpers import wrapper_for

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
