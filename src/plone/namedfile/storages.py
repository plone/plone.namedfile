# This file was borrowed from z3c.blobfile and is licensed under the terms of
# the ZPL.
from OFS.Image import Pdata
from plone.namedfile.file import FileChunk
from plone.namedfile.interfaces import IStorage
from plone.namedfile.interfaces import NotStorable
from zope.interface import implementer
from zope.publisher.browser import FileUpload

import io


MAXCHUNKSIZE = 1 << 16


@implementer(IStorage)
class BytesStorable:
    def store(self, data, blob):
        if not isinstance(data, bytes):
            raise NotStorable("Could not store data (not of bytes type).")

        with blob.open("w") as fp:
            fp.write(data)


@implementer(IStorage)
class TextStorable(BytesStorable):
    def store(self, data, blob):
        if not isinstance(data, str):
            raise NotStorable('Could not store data (not of "unicode" type).')

        data = data.encode("UTF-8")
        BytesStorable.store(self, data, blob)


@implementer(IStorage)
class UnicodeStorable(TextStorable):
    pass


@implementer(IStorage)
class StringStorable(BytesStorable):
    pass


@implementer(IStorage)
class FileChunkStorable:
    def store(self, data, blob):
        if not isinstance(data, FileChunk):
            raise NotStorable(
                'Could not store data (not a of "FileChunk" type).'
            )  # noqa

        with blob.open("w") as fp:
            chunk = data
            while chunk:
                fp.write(chunk._data)
                chunk = chunk.next


@implementer(IStorage)
class FileDescriptorStorable:
    def store(self, data, blob):
        if not isinstance(data, io.IOBase):
            raise NotStorable('Could not store data: not of io.IOBase ("file").')

        filename = getattr(data, "name", None)
        if filename is not None:
            blob.consumeFile(filename)
            return


class BufferedReaderStorable:
    def store(self, data, blob):
        raw = data.raw
        if not isinstance(raw, io.FileIO):
            raise NotStorable('Could not store data (not of type "io.FileIO")')

        filename = getattr(data.raw, "name", None)
        if filename is not None:
            blob.consumeFile(filename)
            return


@implementer(IStorage)
class FileUploadStorable:
    def store(self, data, blob):
        if not isinstance(data, FileUpload):
            raise NotStorable('Could not store data (not of "FileUpload").')

        data.seek(0)

        with blob.open("w") as fp:
            block = data.read(MAXCHUNKSIZE)
            while block:
                fp.write(block)
                block = data.read(MAXCHUNKSIZE)


@implementer(IStorage)
class PDataStorable:
    def store(self, pdata, blob):
        if not isinstance(pdata, Pdata):
            raise NotStorable('Could not store data (not of "Pdata").')
        fp = blob.open("w")
        fp.write(bytes(pdata))
        fp.close()


@implementer(IStorage)
class Zope2FileUploadStorable:
    def store(self, data, blob):
        data.seek(0)
        with blob.open("w") as fp:
            block = data.read(MAXCHUNKSIZE)
            while block:
                fp.write(block)
                block = data.read(MAXCHUNKSIZE)
