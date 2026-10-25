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

from contextlib import contextmanager
from DateTime import DateTime
from plone.namedfile import storages
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.interfaces import INamedBlobFile
from plone.namedfile.interfaces import INamedBlobImage
from plone.namedfile.interfaces import IStorage
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.testing import PLONE_NAMEDFILE_INTEGRATION_TESTING
from plone.namedfile.tests import getFile
from plone.namedfile.tests import MockNamedBlobImage
from plone.namedfile.tests.test_image import zptlogo
from unittest.mock import patch
from ZODB.blob import Blob
from ZODB.blob import BlobStorage
from ZODB.DB import DB
from ZODB.MappingStorage import MappingStorage
from zope.component import provideUtility
from zope.interface.verify import verifyClass

import shutil
import struct
import tempfile
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

    def testDataMutatorWithJPGHeaderLargerThanMaxInfoBytes(self):
        from plone.namedfile.file import MAX_INFO_BYTES

        # APP2 segments of maximum length in front of the frame header.
        segment = b"\xff\xe2" + struct.pack(">H", 0xFFFF) + b"\x00" * 0xFFFD
        jpeg = getFile("image.jpg")
        data = jpeg[:2] + segment * (MAX_INFO_BYTES // len(segment) + 1) + jpeg[2:]
        image = self._makeImage()
        image._setData(data)
        self.assertEqual((image._width, image._height), (500, 200))

    def testDataMutatorWithSVGHeaderLargerThanMaxInfoBytes(self):
        from plone.namedfile.file import MAX_INFO_BYTES

        data = (
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'width="1024px" '
            b'height="680px" '
            b'foobar="' + b"d" * MAX_INFO_BYTES + b'">'
            b"</svg>"
        )
        image = self._makeImage()
        image._setData(data)
        self.assertEqual((image._width, image._height), (1024, 680))

    def testDataMutatorWithTIFFImageFileDirectoryAtTheEnd(self):
        # image.tif has its image file directory after the image data,
        # so only the full data gives the dimensions.
        image = self._makeImage()
        image._setData(getFile("image.tif"))
        self.assertEqual((image._width, image._height), (500, 200))


@contextmanager
def count_blob_opens():
    opens = []
    original_open = Blob.open

    def counting_open(self, mode="r"):
        opens.append(mode)
        return original_open(self, mode)

    with patch.object(Blob, "open", counting_open):
        yield opens


class TestPersistedMetadata(unittest.TestCase):
    """Size and dimensions are stored at write time.

    Reading them must neither open the blob, which may mean downloading it
    from a remote blob storage, nor write to the database.
    """

    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def setUp(self):
        self.blob_dir = tempfile.mkdtemp()
        self.db = DB(BlobStorage(self.blob_dir, MappingStorage()))
        self.tm = transaction.TransactionManager()
        self.conn = self.db.open(self.tm)

    def tearDown(self):
        self.tm.abort()
        self.conn.close()
        self.db.close()
        shutil.rmtree(self.blob_dir)

    def _store(self, obj):
        self.conn.root()["obj"] = obj
        return self._reload(obj)

    def _reload(self, obj):
        """Commit and turn obj into a ghost, it is loaded again on access."""
        self.tm.commit()
        obj._p_invalidate()
        return obj

    def _make_old(self, obj):
        """Store obj like versions without persisted size did."""
        # Accessing __dict__ does not load a ghost.
        obj._p_activate()
        obj.__dict__.pop("size", None)
        obj._p_changed = True
        return self._reload(obj)

    def test_size_is_persisted_on_create(self):
        file = self._store(NamedBlobFile(b"x" * 1000))
        with count_blob_opens() as opens:
            self.assertEqual(file.getSize(), 1000)
        self.assertEqual(opens, [])

    def test_size_is_persisted_on_data_change(self):
        file = self._store(NamedBlobFile(b"x" * 1000))
        file.data = b"y" * 10
        self._reload(file)
        with count_blob_opens() as opens:
            self.assertEqual(file.getSize(), 10)
        self.assertEqual(opens, [])

    def test_open_for_writing_drops_persisted_size(self):
        file = self._store(NamedBlobFile(b"x" * 1000))
        with file.open("w") as fp:
            fp.write(b"y" * 10)
        self._reload(file)
        self.assertEqual(file.getSize(), 10)

    def test_open_for_reading_does_not_write(self):
        file = self._store(NamedBlobFile(b"x" * 1000))
        for mode in ("r", "c"):
            file.open(mode).close()
            self.assertFalse(file._p_changed)
        self.assertEqual(file.getSize(), 1000)

    def test_size_of_old_object_is_backfilled_on_read(self):
        file = self._make_old(self._store(NamedBlobFile(b"x" * 1000)))
        self.assertEqual(file.getSize(), 1000)
        self.assertTrue(file._p_changed)
        self._reload(file)
        with count_blob_opens() as opens:
            self.assertEqual(file.getSize(), 1000)
        self.assertEqual(opens, [])

    def test_size_of_old_object_is_not_written_if_disabled(self):
        file = self._make_old(self._store(NamedBlobFile(b"x" * 1000)))
        with patch("plone.namedfile.file.BACKFILL_ON_READ", False):
            with count_blob_opens() as opens:
                self.assertEqual(file.getSize(), 1000)
                self.assertEqual(file.getSize(), 1000)
        self.assertEqual(len(opens), 1)
        self.assertFalse(file._p_changed)

    def test_backfill_on_read_is_a_safe_write(self):
        # Otherwise plone.protect aborts the transaction on a GET request.
        file = self._make_old(self._store(NamedBlobFile(b"x" * 1000)))
        with patch("plone.namedfile.file.safeWrite") as safe_write:
            file.getSize()
            file.getSize()
        safe_write.assert_called_once_with(file)

    def test_backfill_metadata_keeps_modified(self):
        # Objects written before plone.namedfile 6.2.0 have no _modified,
        # their modification time falls back to _p_mtime.
        file = self._store(NamedBlobFile(b"x" * 1000))
        del file._modified
        self._make_old(file)
        modified = DateTime(file.modified).millis()
        mtime = file._p_mtime
        time.sleep(0.01)  # make sure the next commit is a few ms later
        self.assertTrue(file.backfill_metadata())
        self._reload(file)
        self.assertEqual(DateTime(file.modified).millis(), modified)
        self.assertNotEqual(file._p_mtime, mtime)

    def test_backfill_metadata_stores_size(self):
        file = self._make_old(self._store(NamedBlobFile(b"x" * 1000)))
        # The size read before must not hide that it is not persisted.
        with patch("plone.namedfile.file.BACKFILL_ON_READ", False):
            file.getSize()
        self.assertTrue(file.backfill_metadata())
        self._reload(file)
        with count_blob_opens() as opens:
            self.assertEqual(file.getSize(), 1000)
        self.assertEqual(opens, [])

    def test_backfill_metadata_does_not_write_if_complete(self):
        file = self._store(NamedBlobFile(b"x" * 1000))
        self.assertFalse(file.backfill_metadata())
        self.assertFalse(file._p_changed)

    def test_getImageSize_does_not_read_or_write(self):
        image = self._store(NamedBlobImage(b"not an image"))
        with count_blob_opens() as opens:
            self.assertEqual(image.getImageSize(), (-1, -1))
        self.assertEqual(opens, [])
        self.assertFalse(image._p_changed)

    def test_backfill_metadata_stores_image_size(self):
        data = getFile("image.tif")
        image = self._store(NamedBlobImage(data))
        image._width = image._height = -1
        self._make_old(image)
        self.assertTrue(image.backfill_metadata())
        self._reload(image)
        with count_blob_opens() as opens:
            self.assertEqual(image.getImageSize(), (500, 200))
            self.assertEqual(image.getSize(), len(data))
        self.assertEqual(opens, [])

    def test_backfill_metadata_does_not_write_unknown_image(self):
        image = self._store(NamedBlobImage(b"not an image"))
        self.assertFalse(image.backfill_metadata())
        self.assertFalse(image._p_changed)

    def test_image_size_of_old_object_is_backfilled_on_read(self):
        data = getFile("image.tif")
        image = self._store(NamedBlobImage(data))
        image._width = image._height = -1
        self._make_old(image)
        self.assertEqual(image.getImageSize(), (500, 200))
        self.assertTrue(image._p_changed)
        self._reload(image)
        with count_blob_opens() as opens:
            self.assertEqual(image.getImageSize(), (500, 200))
            self.assertEqual(image.getSize(), len(data))
        self.assertEqual(opens, [])

    def test_image_size_of_old_object_is_not_read_if_disabled(self):
        image = self._store(NamedBlobImage(getFile("image.tif")))
        image._width = image._height = -1
        self._make_old(image)
        with patch("plone.namedfile.file.BACKFILL_ON_READ", False):
            with count_blob_opens() as opens:
                self.assertEqual(image.getImageSize(), (-1, -1))
        self.assertEqual(opens, [])
        self.assertFalse(image._p_changed)

    def test_unknown_old_image_is_read_only_once(self):
        from plone.namedfile.file import MAX_INFO_BYTES

        image = self._store(NamedBlobImage(b"\x00" * MAX_INFO_BYTES * 2))
        self._make_old(image)
        self.assertEqual(image.getImageSize(), (-1, -1))
        self._reload(image)
        with count_blob_opens() as opens:
            self.assertEqual(image.getImageSize(), (-1, -1))
        self.assertEqual(opens, [])
        self.assertFalse(image._p_changed)


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
