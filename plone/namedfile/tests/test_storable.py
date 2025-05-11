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
from plone.namedfile import field
from plone.namedfile.file import FileChunk
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.tests import getFile
from unittest.mock import patch
from ZODB.blob import Blob
from ZODB.blob import BlobFile

import io
import os
import piexif
import PIL
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

        old_open = Blob.open
        blob_read = 0
        blob_write = 0
        old_read = BlobFile.read
        read_bytes = 0

        def count_open(self, mode="r"):
            nonlocal blob_read, blob_write
            blob_read += 1 if "r" in mode else 0
            blob_write += 1 if "w" in mode else 0
            return old_open(self, mode)

        def count_reads(self, size=-1):
            nonlocal read_bytes
            res = old_read(self, size)
            read_bytes += len(res)
            return res

        with patch.object(Blob, "open", count_open), patch.object(
            BlobFile, "read", count_reads
        ):
            data = getFile("image.jpg")
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
            self.assertEqual(3641, fi.getSize())
            self.assertIn("Exif", fi.exif)
            self.assertEqual(500, fi._width)
            self.assertEqual(200, fi._height)
            self.assertLess(
                read_bytes,
                fi.getSize(),
                "Images should not need to read all data to get exif, dimensions",
            )
            self.assertEqual(
                blob_read, 3, "blob opening for getsize, get_exif and getImageInfo only"
            )
            self.assertEqual(
                blob_write,
                1,
                "Slow write to blob instead of os rename. Should be only 1 on __init__ to create empty file",
            )

            # Test validation which should also not read all the data.
            blob_read = read_bytes = 0

            blob_field = field.NamedBlobImage()
            blob_field.validate(fi)
            blob_field = field.NamedBlobFile()  # Image is subclass of file
            blob_field.validate(fi)

            self.assertEqual(
                blob_read, 0, "Validation is reading the whole blob in memory"
            )
            self.assertEqual(
                read_bytes, 0, "Validation is reading the whole blob in memory"
            )

    def test_large_webp_storable(self):
        # ensure we don't read the whole file into memory

        old_open = Blob.open
        blob_read = 0
        blob_write = 0
        old_read = BlobFile.read
        read_bytes = 0

        def count_open(self, mode="r"):
            nonlocal blob_read, blob_write
            blob_read += 1 if "r" in mode else 0
            blob_write += 1 if "w" in mode else 0
            return old_open(self, mode)

        def count_reads(self, size=-1):
            nonlocal read_bytes
            res = old_read(self, size)
            read_bytes += len(res)
            return res

        with patch.object(Blob, "open", count_open), patch.object(
            BlobFile, "read", count_reads
        ):
            fi = NamedBlobImage(getFile("900.webp"), filename="900.webp")
            self.assertEqual((900, 900), fi.getImageSize())
            self.assertLess(
                read_bytes,
                fi.getSize(),
                "Images should not need to read all data to get exif, dimensions",
            )
            self.assertEqual(
                blob_read, 3, "blob opening for getsize, get_exif and getImageInfo only"
            )

    def test_rotate(self):
        # Create a 200x200 white image
        img = PIL.Image.new("RGB", (100, 400), "white")
        # Set the top-left pixels to black
        img.putpixel((0, 0), (0, 0, 0))

        # 270 degree rotation
        # Create EXIF dict
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif_dict["0th"][piexif.ImageIFD.Orientation] = 6
        exif_bytes = piexif.dump(exif_dict)
        # Save image as JPEG with EXIF data
        out = io.BytesIO()
        img.save(out, format="JPEG", exif=exif_bytes)
        fi_jpg = NamedBlobImage(out.getvalue(), filename="image.jpg")
        img_jpg = PIL.Image.open(io.BytesIO(fi_jpg.data))
        self.assertEqual(fi_jpg.getImageSize(), (400, 100))
        self.assertEqual(img_jpg.getpixel((0, 0)), (255, 255, 255))
        # The pixel is not exactly black (RGB 0,0,0) due to quantization errors and
        # compression artifacts introduced by the JPEG encoding process.
        self.assertEqual(img_jpg.getpixel((399, 0)), (10, 10, 10))
        self.assertEqual(img_jpg.getpixel((0, 99)), (255, 255, 255))
        self.assertEqual(img_jpg.getpixel((399, 99)), (255, 255, 255))

        # flip left to right
        # Create EXIF dict
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif_dict["0th"][piexif.ImageIFD.Orientation] = 2
        exif_bytes = piexif.dump(exif_dict)
        # Save image as JPEG with EXIF data
        out = io.BytesIO()
        img.save(out, format="JPEG", exif=exif_bytes)
        fi_jpg = NamedBlobImage(out.getvalue(), filename="image.jpg")
        img_jpg = PIL.Image.open(io.BytesIO(fi_jpg.data))
        self.assertEqual(fi_jpg.getImageSize(), (100, 400))
        self.assertEqual(img_jpg.getpixel((0, 0)), (255, 255, 255))
        # The pixel is not exactly black (RGB 0,0,0) due to quantization errors and
        # compression artifacts introduced by the JPEG encoding process.
        self.assertEqual(img_jpg.getpixel((99, 0)), (8, 8, 8))
        self.assertEqual(img_jpg.getpixel((0, 399)), (255, 255, 255))
        self.assertEqual(img_jpg.getpixel((99, 399)), (255, 255, 255))
