from zope.interface import Interface

from zope import schema
from zope.schema.interfaces import IObject

from zope.app.file.interfaces import IFile, IImage
from z3c.blobfile.interfaces import IBlobFile, IBlobImage

# File objects

class INamed(Interface):
    """An item with a filename
    """
    
    filename = schema.TextLine(title=u"Filename", required=False, default=None)

class IBlobby(Interface):
    """Marker interface for objects that support blobs.
    """

class INamedFile(INamed, IFile):
    """A non-BLOB file with a filename
    """
    
class INamedBlobFile(INamedFile, IBlobby, IBlobFile):
    """A BLOB file with a filename
    """

class INamedImage(INamed, IImage):
    """A non-BLOB image with a filename
    """

class INamedBlobImage(INamedImage, IBlobby, IBlobImage):
    """A BLOB image with a filename
    """

# Fields

class INamedFileField(IObject):
    """Field for storing INamedFile objects.
    """

class INamedImageField(IObject):
    """Field for storing INamedImage objects.
    """

class INamedBlobFileField(IObject):
    """Field for storing INamedBlobFile objects.
    """

class INamedBlobImageField(IObject):
    """Field for storing INamedBlobImage objects.
    """