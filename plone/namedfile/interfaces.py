# -*- coding: utf-8 -*-
from zope import schema
from zope.interface import Interface
from zope.schema.interfaces import IObject


HAVE_BLOBS = True


class IFile(Interface):

    contentType = schema.BytesLine(
        title=u'Content Type',
        description=u'The content type identifies the type of data.',
        default='',
        required=False,
        missing_value=''
    )

    data = schema.Bytes(
        title=u'Data',
        description=u'The actual content of the object.',
        default='',
        missing_value='',
        required=False,
    )

    def getSize():
        """Return the byte-size of the data of the object."""


class IImage(IFile):
    """This interface defines an Image that can be displayed.
    """

    def getImageSize():
        """Return a tuple (x, y) that describes the dimensions of
        the object.
        """


class IImageScaleTraversable(Interface):
    """Marker for items that should provide access to image scales for named
    image fields via the @@images view.
    """


class IAvailableSizes(Interface):
    """A callable returning a dictionary of scale name => (width, height)
    """


try:
    from plone.app.imaging.interfaces import IStableImageScale
except ImportError:
    class IStableImageScale(Interface):
        """ Marker for image scales when accessed with a UID-based URL.
        These can be cached forever using the plone.stableResource ruleset.
        """


# Values

class INamed(Interface):
    """An item with a filename
    """

    filename = schema.TextLine(title=u'Filename', required=False, default=None)


class INamedFile(INamed, IFile):
    """A non-BLOB file with a filename
    """


class INamedImage(INamed, IImage):
    """A non-BLOB image with a filename
    """


# Fields

class INamedField(IObject):
    """Base field type
    """


class INamedFileField(INamedField):
    """Field for storing INamedFile objects.
    """


class INamedImageField(INamedField):
    """Field for storing INamedImage objects.
    """


class IStorage(Interface):
    """Store file data
    """

    def store(data, blob):
        """Store the data into the blob
        Raises NonStorable if data is not storable.
        """


class NotStorable(Exception):
    """Data is not storable
    """


# Values

class IBlobby(Interface):
    """Marker interface for objects that support blobs.
    """


class INamedBlobFile(INamedFile, IBlobby):
    """A BLOB file with a filename
    """


class INamedBlobImage(INamedImage, IBlobby):
    """A BLOB image with a filename
    """


# Fields

class INamedBlobFileField(INamedFileField):
    """Field for storing INamedBlobFile objects.
    """


class INamedBlobImageField(INamedImageField):
    """Field for storing INamedBlobImage objects.
    """
