# -*- coding: utf-8 -*-

import unittest

from plone.namedfile.file import NamedImage
from plone.namedfile.tests import getFile
from plone.namedfile.utils import get_contenttype
from plone.namedfile.utils.svg_utils import dimension_int
from plone.namedfile.utils.svg_utils import process_svg


class TestSvg(unittest.TestCase):

    def test_get_contenttype(self):
        self.assertEqual(
            get_contenttype(
                NamedImage(
                    getFile('image.svg'),
                    contentType='image/svg+xml')),
            'image/svg+xml')

    def test_process_svg(self):

        content_type, width, height = process_svg(getFile('image.svg'))
        self.assertEqual(content_type, "image/svg+xml")
        self.assertEqual(width, 158)
        self.assertEqual(height, 40)

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
        self.assertEqual(dimension_int(getFile('image.svg')), 0)
