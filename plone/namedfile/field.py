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
from plone.namedfile.interfaces import INamedTyped
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

import mimetypes


_ = MessageFactory("plone")


class InvalidFile(ValidationError):
    """Exception for a invalid file."""

    __doc__ = _("Invalid file")


class InvalidImageFile(ValidationError):
    """Exception for a invalid image file."""

    __doc__ = _("Invalid image file")


class BinaryContenttypeValidator:
    def __init__(self, field, value):
        self.field = field
        self.value = value

    def __call__(self):
        if self.value is None:
            return

        if not self.field.accept:
            # No restrictions.
            return

        mimetype = get_contenttype(self.value)

        for accept in self.field.accept:
            if accept[0] == ".":
                # This is a file extension. Get a media type from it.
                accept = mimetypes.guess_type(f"dummy{accept}", strict=False)[0]
                if accept is None:
                    # This extension is unknown. Skip it.
                    continue

            try:
                accept_type, accept_subtype = accept.split("/")
                content_type, content_subtype = mimetype.split("/")
            except ValueError:
                # The accept type is invalid. Skip it.
                continue

            if accept_type == content_type and (
                accept_subtype == content_subtype or accept_subtype == "*"
            ):
                # This file is allowed, just don't raise a ValidationError.
                return

        # The file's content type is not allowed. Raise a ValidationError.
        raise self.exception(mimetype, self.field.__name__)


@implementer(IPluggableFileFieldValidation)
@adapter(INamedFileField, Interface)
class FileContenttypeValidator(BinaryContenttypeValidator):
    exception = InvalidFile


@implementer(IPluggableImageFieldValidation)
@adapter(INamedImageField, Interface)
class ImageContenttypeValidator(BinaryContenttypeValidator):
    exception = InvalidImageFile


class NamedField(Object):

    def __init__(self, **kw):
        if "accept" in kw:
            self.accept = kw.pop("accept")
        if "schema" in kw:
            self.schema = kw.pop("schema")
        super().__init__(schema=self.schema, **kw)

    def validate(self, value, interface):
        super().validate(value)
        for name, validator in getAdapters((self, value), interface):
            validator()


@implementer(INamedFileField)
class NamedFile(NamedField):
    """A NamedFile field"""

    _type = FileValueType
    schema = INamedFile
    accept = ()

    def validate(self, value):
        super().validate(value, IPluggableFileFieldValidation)


@implementer(INamedImageField)
class NamedImage(NamedField):
    """A NamedImage field"""

    _type = ImageValueType
    schema = INamedImage
    accept = ("image/*",)

    def validate(self, value):
        super().validate(value, IPluggableImageFieldValidation)


@implementer(INamedBlobFileField)
class NamedBlobFile(NamedField):
    """A NamedBlobFile field"""

    _type = BlobFileValueType
    schema = INamedBlobFile
    accept = ()

    def validate(self, value):
        # Bit of a hack but we avoid loading the .data into memory
        # because schema validation checks the property exists
        # which loads the entire file into memory without checking the data.
        # This can slow down imports and uploads a lot.
        # TODO: mighe be better fixed in zope.schema - https://github.com/zopefoundation/zope.schema/issues/127
        self.schema = INamedTyped
        try:
            super().validate(value, IPluggableFileFieldValidation)
        finally:
            self.schema = INamedBlobFile


@implementer(INamedBlobImageField)
class NamedBlobImage(NamedField):
    """A NamedBlobImage field"""

    _type = BlobImageValueType
    schema = INamedBlobImage
    accept = ("image/*",)

    def validate(self, value):
        # see NamedBlobFile comment
        self.schema = INamedTyped
        try:
            super().validate(value, IPluggableImageFieldValidation)
        finally:
            self.schema = INamedBlobImage
