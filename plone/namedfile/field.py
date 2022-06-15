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
from plone.namedfile.interfaces import IPluggableFileFieldValidation
from plone.namedfile.interfaces import IPluggableImageFieldValidation
from plone.namedfile.utils import get_contenttype
from zope.component import adapter
from zope.component import getAdapters
from zope.i18nmessageid import MessageFactory
from zope.interface import implementer
from zope.interface import Interface
from zope.schema import Object
from zope.schema import ValidationError


_ = MessageFactory("plone")


@implementer(IPluggableImageFieldValidation)
@adapter(INamedImageField, Interface)
class ImageContenttypeValidator:
    def __init__(self, field, value):
        self.field = field
        self.value = value

    def __call__(self):
        if self.value is None:
            return
        mimetype = get_contenttype(self.value)
        if mimetype.split("/")[0] != "image":
            raise InvalidImageFile(mimetype, self.field.__name__)


class InvalidImageFile(ValidationError):
    """Exception for invalid image file"""

    __doc__ = _("Invalid image file")


def validate_binary_field(interface, field, value):
    for name, validator in getAdapters((field, value), interface):
        validator()


def validate_image_field(field, value):
    validate_binary_field(IPluggableImageFieldValidation, field, value)


def validate_file_field(field, value):
    validate_binary_field(IPluggableFileFieldValidation, field, value)


@implementer(INamedFileField)
class NamedFile(Object):
    """A NamedFile field"""

    _type = FileValueType
    schema = INamedFile

    def __init__(self, **kw):
        if "schema" in kw:
            self.schema = kw.pop("schema")
        super().__init__(schema=self.schema, **kw)

    def _validate(self, value):
        super()._validate(value)
        validate_file_field(self, value)


@implementer(INamedImageField)
class NamedImage(Object):
    """A NamedImage field"""

    _type = ImageValueType
    schema = INamedImage

    def __init__(self, **kw):
        if "schema" in kw:
            self.schema = kw.pop("schema")
        super().__init__(schema=self.schema, **kw)

    def _validate(self, value):
        super()._validate(value)
        validate_image_field(self, value)


@implementer(INamedBlobFileField)
class NamedBlobFile(Object):
    """A NamedBlobFile field"""

    _type = BlobFileValueType
    schema = INamedBlobFile

    def __init__(self, **kw):
        if "schema" in kw:
            self.schema = kw.pop("schema")
        super().__init__(schema=self.schema, **kw)

    def _validate(self, value):
        super()._validate(value)
        validate_file_field(self, value)


@implementer(INamedBlobImageField)
class NamedBlobImage(Object):
    """A NamedBlobImage field"""

    _type = BlobImageValueType
    schema = INamedBlobImage

    def __init__(self, **kw):
        if "schema" in kw:
            self.schema = kw.pop("schema")
        super().__init__(schema=self.schema, **kw)

    def _validate(self, value):
        super()._validate(value)
        validate_image_field(self, value)
