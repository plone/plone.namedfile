from DateTime import DateTime
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.file import NamedImage

import os


def getFile(filename, length=None):
    """return contents of the file with the given name"""
    filename = os.path.join(os.path.dirname(__file__), filename)
    with open(filename, "rb") as data_file:
        return data_file.read(length)


class MockNamedImage(NamedImage):
    _p_mtime = DateTime().millis()


class MockNamedBlobImage(NamedBlobImage):
    _p_mtime = DateTime().millis()
