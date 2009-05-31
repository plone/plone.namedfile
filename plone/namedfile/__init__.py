from plone.namedfile.file import NamedFile, NamedImage

from plone.namedfile.interfaces import HAVE_BLOBS

if HAVE_BLOBS:
    from plone.namedfile.file import NamedBlobFile, NamedBlobImage
