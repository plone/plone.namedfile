from zope.interface import implements
from zope.schema import Object

from plone.namedfile.interfaces import HAVE_BLOBS

from plone.namedfile.interfaces import INamedFileField, INamedImageField

from plone.namedfile.interfaces import INamedFile, INamedImage
from plone.namedfile.file import NamedFile as FileValueType
from plone.namedfile.file import NamedImage as ImageValueType


if HAVE_BLOBS:
    from plone.namedfile.interfaces import INamedBlobFileField, INamedBlobImageField
    from plone.namedfile.interfaces import INamedBlobFile, INamedBlobImage
    
    from plone.namedfile.file import NamedBlobFile as BlobFileValueType
    from plone.namedfile.file import NamedBlobImage as BlobImageValueType

class NamedFile(Object):
    """A NamedFile field
    """
    implements(INamedFileField)
    
    _type = FileValueType
    schema = INamedFile
    
    def __init__(self, **kw):
        if 'schema' in kw:
            self.schema = kw.pop('schema')
        super(NamedFile, self).__init__(schema=self.schema, **kw)

class NamedImage(Object):
    """A NamedImage field
    """
    implements(INamedImageField)
    
    _type = ImageValueType
    schema = INamedImage
    
    def __init__(self, **kw):
        if 'schema' in kw:
            self.schema = kw.pop('schema')
        super(NamedImage, self).__init__(schema=self.schema, **kw)

if HAVE_BLOBS:

    class NamedBlobFile(Object):
        """A NamedBlobFile field
        """
        implements(INamedBlobFileField)
    
        _type = BlobFileValueType
        schema = INamedBlobFile
    
        def __init__(self, **kw):
            if 'schema' in kw:
                self.schema = kw.pop('schema')
            super(NamedBlobFile, self).__init__(schema=self.schema, **kw)

    class NamedBlobImage(Object):
        """A NamedBlobImage field
        """
        implements(INamedBlobImageField)
    
        _type = BlobImageValueType
        schema = INamedBlobImage
    
        def __init__(self, **kw):
            if 'schema' in kw:
                self.schema = kw.pop('schema')
            super(NamedBlobImage, self).__init__(schema=self.schema, **kw)