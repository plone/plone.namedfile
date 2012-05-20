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

from zope.interface import implements
from plone.namedfile.file import FileChunk
from zope.publisher.browser import FileUpload
from plone.namedfile.interfaces import IStorage
from plone.namedfile.interfaces import NotStorable

MAXCHUNKSIZE = 1 << 16


class StringStorable(object):
    implements(IStorage)
     
    def store(self, data, blob):
        if not isinstance(data, str):
            raise NotStorable("Could not store data (not of 'str' type).")

        fp = blob.open('w')
        fp.write(data)
        fp.close()


class UnicodeStorable(StringStorable):
    implements(IStorage)
    
    def store(self, data, blob):
        if not isinstance(data, unicode):
            raise NotStorable("Could not store data (not of 'unicode' "
                              "type).")

        data = data.encode('UTF-8')
        StringStorable.store(self, data, blob)


class FileChunkStorable(object):
    implements(IStorage)
     
    def store(self, data, blob):
        if not isinstance(data, FileChunk):
            raise NotStorable("Could not store data (not a of 'FileChunk' "
                              "type).")

        fp = blob.open('w')
        chunk = data
        while chunk:
            fp.write(chunk._data)
            chunk = chunk.next
        fp.close()


class FileDescriptorStorable(object):
    implements(IStorage)
     
    def store(self, data, blob):
        if not isinstance(data, file):
            raise NotStorable("Could not store data (not of 'file').")

        filename = getattr(data, "name", None)
        if filename is not None:
            blob.consumeFile(filename)
            return


class FileUploadStorable(object):
    implements(IStorage)
     
    def store(self, data, blob):
        if not isinstance(data, FileUpload):
            raise NotStorable("Could not store data (not of 'FileUpload').")

        data.seek(0)

        fp = blob.open('w')
        block = data.read(MAXCHUNKSIZE)
        while block:
            fp.write(block)
            block = data.read(MAXCHUNKSIZE)
        fp.close()
