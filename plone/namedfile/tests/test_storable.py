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

from OFS.Image import Pdata
from plone.namedfile.file import FileChunk
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.file import NamedBlobFile
from plone.namedfile import field
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.tests import getFile

import os
import tempfile
import unittest


class TestStorable(unittest.TestCase):

    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def test_pdata_storable(self):
        pdata = Pdata(getFile("image.gif"))
        fi = NamedBlobImage(pdata, filename="image.gif")
        self.assertEqual(303, fi.getSize())

    def test_str_storable(self):
        fi = NamedBlobImage(getFile("image.gif"), filename="image.gif")
        self.assertEqual(303, fi.getSize())

    def test_filechunk_storable(self):
        fi = NamedBlobImage(FileChunk(getFile("image.gif")), filename="image.gif")
        self.assertEqual(303, fi.getSize())

    def test_opened_file_storable(self):
        data = getFile("image.gif")
        f = tempfile.NamedTemporaryFile(delete=False)
        try:
            path = f.name
            f.write(data)
            f.close()
            with open(path, "rb") as f:
                fi = NamedBlobImage(f, filename="image.gif")
        finally:
            if os.path.exists(path):
                os.remove(path)
        self.assertEqual(303, fi.getSize())

    def test_upload_no_read(self):
        # ensure we don't read the whole file into memory

        import ZODB.blob

        old_open = ZODB.blob.Blob.open
        blob_read = 0
        blob_write = 0

        def count_open(self, mode="r"):
            nonlocal blob_read, blob_write
            blob_read += 1 if "r" in mode else 0
            blob_write += 1 if "w" in mode else 0
            return old_open(self, mode)

        ZODB.blob.Blob.open = count_open

        data = getFile("image.gif")
        f = tempfile.NamedTemporaryFile(delete=False)
        try:
            path = f.name
            f.write(data)
            f.close()
            with open(path, "rb") as f:
                fi = NamedBlobFile(f, filename="image.gif")
        finally:
            if os.path.exists(path):
                os.remove(path)
        self.assertEqual(303, fi.getSize())
        self.assertEqual(blob_read, 1, "blob should have only been opened to get size")
        self.assertEqual(
            blob_write,
            1,
            "Slow write to blob instead of os rename. Should be only 1 on init",
        )
        blob_read = 0

        blob_field = field.NamedBlobFile()
        blob_field.validate(fi)

        self.assertEqual(blob_read, 0, "Validation is reading the whole blob in memory")

        ZODB.blob.Blob.open = old_open
