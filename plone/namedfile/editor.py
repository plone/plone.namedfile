from plone.namedfile import field
from plone.namedfile import interfaces
from plone.schemaeditor.fields import FieldFactory
from zope.i18nmessageid.message import MessageFactory


_ = MessageFactory("plone")


class INamedFileField(interfaces.INamedFileField):

    default = field.NamedFile(
        title=interfaces.INamedFileField["default"].title,
        description=interfaces.INamedFileField["default"].description,
        required=False,
    )

    missing_value = field.NamedFile(
        title=interfaces.INamedFileField["missing_value"].title,
        description=interfaces.INamedFileField["missing_value"].description,
        required=False,
    )


class INamedImageField(interfaces.INamedImageField):

    default = field.NamedImage(
        title=interfaces.INamedImageField["default"].title,
        description=interfaces.INamedImageField["default"].description,
        required=False,
    )

    missing_value = field.NamedImage(
        title=interfaces.INamedImageField["missing_value"].title,
        description=interfaces.INamedImageField["missing_value"].description,
        required=False,
    )


NamedFileFactory = FieldFactory(field.NamedFile, _("File Upload"))
NamedImageFactory = FieldFactory(field.NamedImage, _("Image"))


class INamedBlobFileField(interfaces.INamedBlobFileField):

    default = field.NamedBlobFile(
        title=interfaces.INamedBlobFileField["default"].title,
        description=interfaces.INamedBlobFileField["default"].description,
        required=False,
    )

    missing_value = field.NamedBlobFile(
        title=interfaces.INamedBlobFileField["missing_value"].title,
        description=interfaces.INamedBlobFileField["missing_value"].description,
        required=False,
    )


class INamedBlobImageField(interfaces.INamedBlobImageField):

    default = field.NamedBlobImage(
        title=interfaces.INamedBlobImageField["default"].title,
        description=interfaces.INamedBlobImageField["default"].description,
        required=False,
    )

    missing_value = field.NamedBlobImage(
        title=interfaces.INamedBlobImageField["missing_value"].title,
        description=interfaces.INamedBlobImageField["missing_value"].description,
        required=False,
    )


NamedBlobFileFactory = FieldFactory(field.NamedBlobFile, _("File Upload"))
NamedBlobImageFactory = FieldFactory(field.NamedBlobImage, _("Image"))

class INamedS3FileField(interfaces.INamedS3FileField):

    default = field.NamedS3File(
        title=interfaces.INamedS3FileField["default"].title,
        description=interfaces.INamedS3FileField["default"].description,
        required=False,
    )

    missing_value = field.NamedS3File(
        title=interfaces.INamedS3FileField["missing_value"].title,
        description=interfaces.INamedS3FileField["missing_value"].description,
        required=False,
    )


class INamedS3ImageField(interfaces.INamedS3ImageField):

    default = field.NamedS3Image(
        title=interfaces.INamedS3ImageField["default"].title,
        description=interfaces.INamedS3ImageField["default"].description,
        required=False,
    )

    missing_value = field.NamedS3Image(
        title=interfaces.INamedS3ImageField["missing_value"].title,
        description=interfaces.INamedS3ImageField["missing_value"].description,
        required=False,
    )


NamedS3FileFactory = FieldFactory(field.NamedS3File, _("File Upload"))
NamedS3ImageFactory = FieldFactory(field.NamedS3Image, _("Image"))
