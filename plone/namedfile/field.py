# -*- coding: utf-8 -*-
from plone.namedfile.file import NamedBlobFile as BlobFileValueType
from plone.namedfile.file import NamedBlobImage as BlobImageValueType
from plone.namedfile.file import NamedFile as FileValueType
from plone.namedfile.file import NamedImage as ImageValueType
from plone.namedfile.interfaces import INamedBlobFile
from plone.namedfile.interfaces import INamedBlobFileField
from plone.namedfile.interfaces import INamedBlobImage
from plone.namedfile.interfaces import INamedBlobImageField
from plone.namedfile.interfaces import INamedFile
from plone.namedfile.interfaces import INamedFileField
from plone.namedfile.interfaces import INamedImage
from plone.namedfile.interfaces import INamedImageField
from plone.namedfile.utils import get_contenttype
from zope.i18nmessageid import MessageFactory
from zope.interface import implementer
from zope.schema import Object
from zope.schema import ValidationError


_ = MessageFactory('plone')


class InvalidImageFile(ValidationError):
    """Exception for invalid image file"""
    __doc__ = _(u'Invalid image file')


def validate_image_field(field, value):
    if value is not None:
        mimetype = get_contenttype(value)
        if mimetype.split('/')[0] != 'image':
            raise InvalidImageFile(mimetype, field.__name__)


@implementer(INamedFileField)
class NamedFile(Object):
    """A NamedFile field
    """

    _type = FileValueType
    schema = INamedFile

    def __init__(self, **kw):
        if 'schema' in kw:
            self.schema = kw.pop('schema')
        super(NamedFile, self).__init__(schema=self.schema, **kw)


@implementer(INamedImageField)
class NamedImage(Object):
    """A NamedImage field
    """

    _type = ImageValueType
    schema = INamedImage

    def __init__(self, **kw):
        if 'schema' in kw:
            self.schema = kw.pop('schema')
        super(NamedImage, self).__init__(schema=self.schema, **kw)

    def _validate(self, value):
        super(NamedImage, self)._validate(value)
        validate_image_field(self, value)


@implementer(INamedBlobFileField)
class NamedBlobFile(Object):
    """A NamedBlobFile field
    """

    _type = BlobFileValueType
    schema = INamedBlobFile

    def __init__(self, **kw):
        if 'schema' in kw:
            self.schema = kw.pop('schema')
        super(NamedBlobFile, self).__init__(schema=self.schema, **kw)


@implementer(INamedBlobImageField)
class NamedBlobImage(Object):
    """A NamedBlobImage field
    """

    _type = BlobImageValueType
    schema = INamedBlobImage

    def __init__(self, **kw):
        if 'schema' in kw:
            self.schema = kw.pop('schema')
        super(NamedBlobImage, self).__init__(schema=self.schema, **kw)

    def _validate(self, value):
        super(NamedBlobImage, self)._validate(value)
        validate_image_field(self, value)
