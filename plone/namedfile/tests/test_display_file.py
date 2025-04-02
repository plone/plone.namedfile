from OFS.SimpleItem import SimpleItem
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.base.utils import safe_text
from plone.namedfile import field
from plone.namedfile import file
from plone.namedfile.interfaces import IAvailableSizes
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.tests import getFile
from plone.testing.zope import Browser
from zope.annotation import IAnnotations
from zope.annotation import IAttributeAnnotatable
from zope.component import getSiteManager
from zope.interface import implementer

import transaction
import unittest


class ISchema(IImageScaleTraversable):
    image = field.NamedImage()
    blob_image = field.NamedBlobImage()
    file = field.NamedFile()
    blob_file = field.NamedBlobFile()


@implementer(IAttributeAnnotatable, ISchema)
class DummyContent(SimpleItem):
    # Adapted from test_scaling_functional.py
    image = None
    blob_image = None
    file = None
    blob_file = None
    # modified = DateTime
    id = __name__ = "item"
    title = "foo"

    def Title(self):
        return self.title


def get_disposition_header(browser):
    # Could be CamelCase or all lowercase.
    name = "Content-Disposition"
    if name in browser.headers.keys():
        return browser.headers.get(name)
    name = name.lower()
    return browser.headers.get(name, None)


def custom_available_sizes():
    # Define available image scales.
    return {"custom": (10, 10)}


class TestAttackVectorNamedImage(unittest.TestCase):
    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING
    field_class = file.NamedImage
    field_name = "image"

    def setUp(self):
        self.portal = self.layer["app"]
        item = DummyContent()
        self.layer["app"]._setOb("item", item)
        self.item = self.layer["app"].item
        sm = getSiteManager()
        sm.registerUtility(component=custom_available_sizes, provided=IAvailableSizes)

    def tearDown(self):
        sm = getSiteManager()
        sm.unregisterUtility(provided=IAvailableSizes)

    def get_admin_browser(self):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        browser.addHeader(
            "Authorization",
            f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}",
        )
        return browser

    def get_anon_browser(self):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        return browser

    def _named_file(self, name):
        data = getFile(name)
        return self.field_class(data, filename=safe_text(name))

    def assert_download_works(self, base_url):
        browser = self.get_anon_browser()
        browser.open(base_url + f"/@@download/{self.field_name}")
        header = get_disposition_header(browser)
        self.assertIsNotNone(header)
        self.assertIn("attachment", header)
        self.assertIn("filename", header)

    def assert_display_inline_works(self, base_url):
        # Test that displaying this file inline works.
        browser = self.get_anon_browser()
        browser.open(base_url + f"/@@display-file/{self.field_name}")
        self.assertIsNone(get_disposition_header(browser))

    def assert_display_inline_is_download(self, base_url):
        # Test that displaying this file inline turns into a download.
        browser = self.get_anon_browser()
        browser.open(base_url + f"/@@display-file/{self.field_name}")
        header = get_disposition_header(browser)
        self.assertIsNotNone(header)
        self.assertIn("attachment", header)
        self.assertIn("filename", header)

    def assert_scale_view_works(self, base_url):
        # Test that accessing a scale view shows the image inline.
        browser = self.get_anon_browser()
        browser.open(base_url + f"/@@images/{self.field_name}")
        self.assertIsNone(get_disposition_header(browser))

        # Note: the 'custom' scale is defined in an adapter above.
        browser.open(base_url + f"/@@images/{self.field_name}/custom")
        self.assertIsNone(get_disposition_header(browser))

        unique_scale_id = list(IAnnotations(self.item)["plone.scale"].keys())[0]
        browser.open(base_url + f"/@@images/{unique_scale_id}")
        self.assertIsNone(get_disposition_header(browser))

    def assert_scale_view_is_download(self, base_url):
        # Test that accessing a scale view turns into a download.
        browser = self.get_anon_browser()
        browser.open(base_url + f"/@@images/{self.field_name}")
        header = get_disposition_header(browser)
        self.assertIsNotNone(header)
        self.assertIn("attachment", header)
        self.assertIn("filename", header)

        browser.open(base_url + f"/@@images/{self.field_name}/custom")
        header = get_disposition_header(browser)
        self.assertIsNotNone(header)
        self.assertIn("attachment", header)
        self.assertIn("filename", header)

        unique_scale_id = list(IAnnotations(self.item)["plone.scale"].keys())[0]
        browser.open(base_url + f"/@@images/{unique_scale_id}")
        header = get_disposition_header(browser)
        self.assertIsNotNone(header)
        self.assertIn("attachment", header)
        self.assertIn("filename", header)

    def test_png_image(self):
        setattr(self.item, self.field_name, self._named_file("image.png"))
        transaction.commit()
        base_url = self.item.absolute_url()
        self.assert_download_works(base_url)
        self.assert_display_inline_works(base_url)
        if self.field_name == "image":
            self.assert_scale_view_works(base_url)

    def test_svg_image(self):
        setattr(self.item, self.field_name, self._named_file("image.svg"))
        transaction.commit()
        base_url = self.item.absolute_url()
        self.assert_download_works(base_url)
        self.assert_display_inline_is_download(base_url)
        if self.field_name == "image":
            self.assert_scale_view_is_download(base_url)

    def test_filename_none(self):
        # A 'None' filename probably does not happen during normal upload,
        # but if an attacker manages this, even @@download would show inline.
        # We prevent this.
        data = self._named_file("image.svg")
        data.filename = None
        setattr(self.item, self.field_name, data)
        transaction.commit()
        base_url = self.item.absolute_url()
        self.assert_download_works(base_url)
        self.assert_display_inline_is_download(base_url)
        if self.field_name == "image":
            self.assert_scale_view_is_download(base_url)

    def test_filename_empty(self):
        # An empty filename is probably no problem, but let's check.
        data = self._named_file("image.svg")
        data.filename = ""
        setattr(self.item, self.field_name, self._named_file("image.svg"))
        transaction.commit()
        base_url = self.item.absolute_url()
        self.assert_download_works(base_url)
        self.assert_display_inline_is_download(base_url)
        if self.field_name == "image":
            self.assert_scale_view_is_download(base_url)


class TestAttackVectorNamedBlobImage(TestAttackVectorNamedImage):
    field_class = file.NamedBlobImage


class TestAttackVectorNamedFile(TestAttackVectorNamedImage):
    field_class = file.NamedFile
    field_name = "file"

    def test_html_file(self):
        data = self.field_class(
            "<h1>Attacker</h1>", filename=safe_text("attacker.html")
        )
        setattr(self.item, self.field_name, data)
        transaction.commit()
        base_url = self.item.absolute_url()
        self.assert_download_works(base_url)
        self.assert_display_inline_is_download(base_url)

    def test_pdf(self):
        # By popular request we allow PDF.
        setattr(self.item, self.field_name, self._named_file("file.pdf"))
        transaction.commit()
        base_url = self.item.absolute_url()
        self.assert_download_works(base_url)
        self.assert_display_inline_works(base_url)


class TestAttackVectorNamedBlobFile(TestAttackVectorNamedFile):
    field_class = file.NamedBlobFile
