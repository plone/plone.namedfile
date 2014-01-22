from zope.interface import implements
from zope.schema import Object, ValidationError
from zope.i18nmessageid import MessageFactory

from plone.namedfile.interfaces import INamedFileField, INamedImageField

from plone.namedfile.interfaces import INamedFile, INamedImage
from plone.namedfile.file import NamedFile as FileValueType
from plone.namedfile.file import NamedImage as ImageValueType

from plone.namedfile.interfaces import INamedBlobFileField, INamedBlobImageField
from plone.namedfile.interfaces import INamedBlobFile, INamedBlobImage

from plone.namedfile.file import NamedBlobFile as BlobFileValueType
from plone.namedfile.file import NamedBlobImage as BlobImageValueType
from plone.namedfile.utils import get_contenttype


_ = MessageFactory('plone')

class InvalidImageFile(ValidationError):
    """Exception for invalid image file"""
    __doc__ = _(u"Invalid image file")


def validate_image_field(field, value):
    try:
        validate_image_file(value)
    except InvalidImageFile, error:
        raise InvalidImageFile([error], field.__name__)


def validate_image_file(namedfile):
    if namedfile is not None:
        mimetype = get_contenttype(namedfile)
        if mimetype.split('/')[0] != 'image':
            raise InvalidImageFile(mimetype)


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

    def _validate(self, value):
        super(NamedImage, self)._validate(value)
        validate_image_file(self, value)


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

    def _validate(self, value):
        super(NamedBlobImage, self)._validate(value)
        validate_image_file(self, value)

