# This file was borrowed from z3c.blobfile and is licensed under the terms of
# the ZPL.

##############################################################################
#
# Copyright (c) 2008 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from DateTime import DateTime
from plone.namedfile import storages
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.interfaces import INamedBlobFile
from plone.namedfile.interfaces import INamedBlobImage
from plone.namedfile.interfaces import IStorage
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.testing import PLONE_NAMEDFILE_INTEGRATION_TESTING
from plone.namedfile.tests import MockNamedBlobImage
from plone.namedfile.tests.test_image import zptlogo
from zope.component import provideUtility
from zope.interface.verify import verifyClass

import struct
import time
import transaction
import unittest


def registerUtilities():
    provideUtility(storages.StringStorable(), IStorage, name="__builtin__.str")
    provideUtility(storages.UnicodeStorable(), IStorage, name="__builtin__.unicode")
    provideUtility(
        storages.FileChunkStorable(), IStorage, name="plone.namedfile.file.FileChunk"
    )
    provideUtility(storages.FileDescriptorStorable(), IStorage, name="__builtin__.file")


class TestImage(unittest.TestCase):

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def setUp(self):
        registerUtilities()

    def _makeImage(self, *args, **kw):
        return NamedBlobImage(*args, **kw)

    def testEmpty(self):
        file = self._makeImage()
        self.assertEqual(file.contentType, "")
        self.assertEqual(file.data, b"")
        self.assertIsNotNone(file.modified)

    def testConstructor(self):
        file = self._makeImage(b"Data")
        self.assertEqual(file.contentType, "")
        self.assertEqual(file.data, b"Data")
        self.assertIsNotNone(file.modified)

    def testMutators(self):
        image = self._makeImage()

        image.contentType = "image/jpeg"
        self.assertEqual(image.contentType, "image/jpeg")

        image._setData(zptlogo)
        self.assertEqual(image.data, zptlogo)
        self.assertEqual(image.contentType, "image/gif")
        self.assertEqual(image.getImageSize(), (16, 16))

    def testModifiedTimeStamp(self):
        image = self._makeImage()
        old_timestamp = image.modified
        time.sleep(1 / 1000)  # make sure at least 1ms passes
        now = DateTime()
        self.assertGreater(now, DateTime(old_timestamp))
        image._setData(zptlogo)
        self.assertNotEqual(image.modified, old_timestamp)

    def testFallBackToDatabaseModifiedTimeStamp(self):
        dt = DateTime()
        image = MockNamedBlobImage()
        image._p_mtime = int(dt)
        image._modified = (dt + 1).millis()

        delattr(image, "_modified")
        self.assertEqual(image.modified, image._p_mtime)

    def testInterface(self):
        self.assertTrue(INamedBlobImage.implementedBy(NamedBlobImage))
        self.assertTrue(verifyClass(INamedBlobImage, NamedBlobImage))
        self.assertTrue(INamedBlobFile.implementedBy(NamedBlobImage))
        self.assertTrue(INamedBlobImage.implementedBy(NamedBlobImage))
        self.assertTrue(verifyClass(INamedBlobFile, NamedBlobImage))

    def testDataMutatorWithLargeJPGHeader(self):
        from plone.namedfile.file import IMAGE_INFO_BYTES

        bogus_header_length = struct.pack(">H", IMAGE_INFO_BYTES * 2)
        data = (
            b"\xff\xd8\xff\xe0"
            + bogus_header_length
            + b"\x00" * IMAGE_INFO_BYTES * 2
            + b"\xff\xc0\x00\x11\x08\x02\xa8\x04\x00"
        )
        image = self._makeImage()
        image._setData(data)
        self.assertEqual(image.getImageSize(), (1024, 680))

    def testDataMutatorWithLargeSVGHeader(self):
        from plone.namedfile.file import IMAGE_INFO_BYTES

        to_big_header_data = b"d" * (IMAGE_INFO_BYTES * 2)

        data = (
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'width="1024px" '
            b'height="680px" '
            b'foobar="' + to_big_header_data + b'">'
            b'</svg>"'
        )
        image = self._makeImage()
        image._setData(data)
        self.assertEqual(image.getImageSize(), (1024, 680))
        self.assertGreater(len(to_big_header_data), IMAGE_INFO_BYTES)


class TestImageFunctional(unittest.TestCase):

    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def setUp(self):
        registerUtilities()

    def testCopyBlobs(self):
        from zope.copy import copy

        file = NamedBlobFile()
        file.data = "hello, world"
        image = NamedBlobImage()
        image.data = "some image bytes"
        transaction.commit()

        file_copy = copy(file)
        self.assertEqual(file_copy.data, file.data)

        image_copy = copy(image)
        self.assertEqual(image_copy.data, image.data)
