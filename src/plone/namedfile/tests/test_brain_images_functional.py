from io import BytesIO
from lxml import html as lxml_html
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.namedfile.testing import NAMEDFILE_PLONE_FUNCTIONAL
from plone.namedfile.tests.brain_images_helpers import clear_scales
from plone.namedfile.tests.brain_images_helpers import create_image
from plone.namedfile.tests.brain_images_helpers import get_brain
from plone.testing.zope import Browser
from urllib.error import HTTPError
from zope.component import getMultiAdapter

import PIL
import transaction
import unittest


class BrainImageFunctionalTests(unittest.TestCase):
    """Serve brain-generated URLs and enforce object access."""

    layer = NAMEDFILE_PLONE_FUNCTIONAL

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.obj = create_image(self.portal)
        self.brain = get_brain(self.portal, self.obj)
        self.view = getMultiAdapter((self.brain, self.request), name="images")

    def scale_url(self, scale="thumb"):
        tag = self.view.tag("image", scale=scale)
        return lxml_html.fragment_fromstring(tag).get("src")

    def browser(self):
        browser = Browser(self.layer["app"])
        browser.addHeader("Referer", self.layer["app"].absolute_url())
        return browser

    def testScaleUrlServesImage(self):
        url = self.scale_url()
        transaction.commit()

        browser = self.browser()
        browser.open(url)

        self.assertEqual(browser.headers["content-type"], "image/png")
        image = PIL.Image.open(BytesIO(browser.contents))
        self.assertEqual(image.size, (128, 128))

    def testStaleMetadataUrlReturns404(self):
        url = self.scale_url()
        clear_scales(self.obj)
        transaction.commit()

        browser = self.browser()
        with self.assertRaises(HTTPError) as caught:
            browser.open(url)

        self.assertEqual(caught.exception.code, 404)

    def testAnonymousCannotFetchPrivateImage(self):
        url = self.scale_url()
        self.obj.manage_permission("View", ("Manager",), acquire=0)
        transaction.commit()

        browser = self.browser()
        browser.handleErrors = True
        browser.open(url)

        self.assertNotEqual(browser.headers.get("content-type"), "image/png")
        self.assertNotIn("PNG", browser.contents[:8])
