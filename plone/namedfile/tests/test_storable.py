# -*- coding: utf-8 -*-
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
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.tests import getFile

import unittest


class TestStorable(unittest.TestCase):

    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def setUp(self):
        pass

    def test_pdata_storable(self):
        pdata = Pdata(getFile('image.gif').read())
        fi = NamedBlobImage(pdata, filename=u'image.gif')
        self.assertEqual(303, fi.getSize())

    def test_str_storable(self):
        fi = NamedBlobImage(getFile('image.gif').read(), filename=u'image.gif')
        self.assertEqual(303, fi.getSize())

    def test_filechunk_storable(self):
        fi = NamedBlobImage(FileChunk(getFile('image.gif').read()),
                            filename=u'image.gif')
        self.assertEqual(303, fi.getSize())
