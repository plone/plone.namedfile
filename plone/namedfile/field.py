from plone.namedfile.file import NamedBlobFile as BlobFileValueType
from plone.namedfile.file import NamedBlobImage as BlobImageValueType
from plone.namedfile.file import NamedFile as FileValueType
from plone.namedfile.file import NamedImage as ImageValueType
from plone.namedfile.interfaces import INamedBlobFile, INamedTyped
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
from zope.schema import Field
from zope.schema._bootstrapinterfaces import SchemaNotProvided
from zope.schema._bootstrapinterfaces import SchemaNotCorrectlyImplemented
from zope.schema._bootstrapfields import get_validation_errors

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


class CustomValidator(object):
    """ Mixin that overrides Object._validate with the same code except it will
    use self.validation_schema instead of self.schema. It will also execute
    self.extra_validator if it exists.
    """

    def __init__(self, **kw):
        if "schema" in kw:
            self.schema = kw.pop("schema")
        super().__init__(schema=self.schema, **kw)

    def _validate(self, value):
        super(Object, self)._validate(value)

        # schema has to be provided by value
        if not self.validation_schema.providedBy(value):
            raise SchemaNotProvided(self.validation_schema, value).with_field_and_value(
                self, value)

        # check the value against schema
        schema_error_dict, invariant_errors = get_validation_errors(
            self.validation_schema,
            value,
            self.validate_invariants
        )

        if schema_error_dict or invariant_errors:
            errors = list(schema_error_dict.values()) + invariant_errors
            exception = SchemaNotCorrectlyImplemented(
                errors,
                self.__name__,
                schema_error_dict,
                invariant_errors
            ).with_field_and_value(self, value)

            try:
                raise exception
            finally:
                # Break cycles
                del exception
                del invariant_errors
                del schema_error_dict
                del errors

        if hasattr(self, 'extra_validator'):
            self.extra_validator(value)


@implementer(INamedFileField)
class NamedFile(CustomValidator, Object):
    """A NamedFile field"""

    _type = FileValueType
    schema = INamedFile
    validation_schema = INamedFile
    extra_validator = validate_file_field


@implementer(INamedImageField)
class NamedImage(CustomValidator, Object):
    """A NamedImage field"""

    _type = ImageValueType
    schema = INamedImage
    validation_schema = INamedImage
    extra_validator = validate_image_field


@implementer(INamedBlobFileField)
class NamedBlobFile(CustomValidator, Object):
    """A NamedBlobFile field"""

    _type = BlobFileValueType
    schema = INamedFile
    validation_schema = INamedTyped  # Note: Don't validate data as will read in whole file
    extra_validator = validate_file_field


@implementer(INamedBlobImageField)
class NamedBlobImage(CustomValidator, Object):
    """A NamedBlobImage field"""

    _type = BlobImageValueType
    schema = INamedImage
    validation_schema = INamedTyped  # Note: Don't validate data as will read in whole file
    extra_validator = validate_image_field

