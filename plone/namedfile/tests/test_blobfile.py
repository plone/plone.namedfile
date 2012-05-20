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
import unittest
import struct
import transaction

from zope.component import provideUtility
from zope.interface.verify import verifyClass
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.interfaces import INamedBlobFile
from plone.namedfile.interfaces import INamedBlobImage
from plone.namedfile.interfaces import IStorage
from plone.namedfile import storages
from plone.namedfile.tests.base import NamedFileLayer
from plone.namedfile.tests.test_image import zptlogo


def registerUtilities():
     provideUtility(storages.StringStorable(), IStorage, name="__builtin__.str")
     provideUtility(storages.UnicodeStorable(), IStorage, name="__builtin__.unicode")
     provideUtility(storages.FileChunkStorable(), IStorage, name="plone.namedfile.file.FileChunk")
     provideUtility(storages.FileDescriptorStorable(), IStorage, name="__builtin__.file")


class TestImage(unittest.TestCase):

    layer = NamedFileLayer

    def setUp(self):
        registerUtilities()

    def _makeImage(self, *args, **kw):
        return NamedBlobImage(*args, **kw)

    def testEmpty(self):
        file = self._makeImage()
        self.assertEqual(file.contentType, '')
        self.assertEqual(file.data, '')

    def testConstructor(self):
        file = self._makeImage('Data')
        self.assertEqual(file.contentType, '')
        self.assertEqual(file.data, 'Data')

    def testMutators(self):
        image = self._makeImage()

        image.contentType = 'image/jpeg'
        self.assertEqual(image.contentType, 'image/jpeg')

        image._setData(zptlogo)
        self.assertEqual(image.data, zptlogo)
        self.assertEqual(image.contentType, 'image/gif')
        self.assertEqual(image.getImageSize(), (16, 16))

    def testInterface(self):
        self.failUnless(INamedBlobImage.implementedBy(NamedBlobImage))
        self.failUnless(verifyClass(INamedBlobImage, NamedBlobImage))
        self.failUnless(INamedBlobFile.implementedBy(NamedBlobImage))
        self.failUnless(INamedBlobImage.implementedBy(NamedBlobImage))
        self.failUnless(verifyClass(INamedBlobFile, NamedBlobImage))
    
    def testDataMutatorWithLargeHeader(self):
        from plone.namedfile.file import IMAGE_INFO_BYTES
        bogus_header_length = struct.pack('>H', IMAGE_INFO_BYTES * 2)
        data = ('\xff\xd8\xff\xe0' + bogus_header_length +
                '\x00' * IMAGE_INFO_BYTES * 2 +
                '\xff\xc0\x00\x11\x08\x02\xa8\x04\x00')
        image = self._makeImage()
        image._setData(data)
        self.assertEqual(image.getImageSize(), (1024, 680))

    def testCopyBlobs(self):
        from zope.copy import copy
        file = NamedBlobFile()
        file.data = u'hello, world'
        image = NamedBlobImage()
        image.data = 'some image bytes'
        transaction.commit()

        file_copy = copy(file)
        self.assertEqual(file_copy.data, file.data)

        image_copy = copy(image)
        self.assertEqual(image_copy.data, image.data)
    