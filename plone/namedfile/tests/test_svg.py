from plone.namedfile.file import NamedImage
from plone.namedfile.tests import getFile
from plone.namedfile.utils import get_contenttype
from plone.namedfile.utils.svg_utils import dimension_int
from plone.namedfile.utils.svg_utils import process_svg

import unittest


class TestSvg(unittest.TestCase):
    def test_get_contenttype(self):
        self.assertEqual(
            get_contenttype(
                NamedImage(getFile("image.svg"), contentType="image/svg+xml")
            ),
            "image/svg+xml",
        )

    def test_process_svg(self):

        content_type, width, height = process_svg(getFile("image.svg"))
        self.assertEqual(content_type, "image/svg+xml")
        self.assertEqual(width, 158)
        self.assertEqual(height, 40)

    def test_process_svg__indicate_header_truncation(self):
        """Check that we can detect SVG files where the file header was
        larger than the requested first bytes. process_svg() should
        return -1 as dimensions to indicate the truncation."""

        truncated_data = getFile("image_large_header.svg", length=1024)
        content_type, width, height = process_svg(truncated_data)
        self.assertEqual(content_type, "image/svg+xml")
        self.assertEqual(width, -1)
        self.assertEqual(height, -1)

    def test_process_svg__can_handle_large_header(self):

        data = getFile("image_large_header.svg")
        content_type, width, height = process_svg(data)
        self.assertEqual(content_type, "image/svg+xml")
        self.assertEqual(width, 1041)
        self.assertEqual(height, 751)

    def test_dimension_int(self):

        self.assertEqual(dimension_int("auto"), 0)
        self.assertEqual(dimension_int("0"), 0)
        self.assertEqual(dimension_int("25"), 25)
        self.assertEqual(dimension_int("1024px"), 1024)
        self.assertEqual(dimension_int("123.0025px"), 123)
        self.assertEqual(dimension_int("123.625pt"), 123)
        self.assertEqual(dimension_int("50%"), 50)
        self.assertEqual(dimension_int(42), 42)
        self.assertEqual(dimension_int(6.25), 6)
        self.assertEqual(dimension_int({}), 0)
        self.assertEqual(dimension_int([]), 0)
        self.assertEqual(dimension_int(getFile("image.svg")), 0)
