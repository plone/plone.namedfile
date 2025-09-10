from zope import schema
from zope.i18nmessageid import MessageFactory
from zope.interface import Interface
from zope.schema.interfaces import IObject


# We don't have translations here, but this allows
_ = MessageFactory("plone")


HAVE_BLOBS = True


class ITyped(Interface):

    contentType = schema.NativeStringLine(
        title="Content Type",
        description="The content type identifies the type of data.",
        default="",
        required=False,
        missing_value="",
    )


class IFile(Interface):

    data = schema.Bytes(
        title="Data",
        description="The actual content of the object.",
        default=b"",
        missing_value="",
        required=False,
    )

    def getSize():
        """Return the byte-size of the data of the object."""


class IImage(IFile):
    """This interface defines an Image that can be displayed."""

    def getImageSize():
        """Return a tuple (x, y) that describes the dimensions of
        the object.
        """


class IImageScaleTraversable(Interface):
    """Marker for items that should provide access to image scales for named
    image fields via the @@images view.
    """


class IAvailableSizes(Interface):
    """A callable returning a dictionary of scale name => (width, height)"""


class IStableImageScale(Interface):
    """Marker for image scales when accessed with a UID-based URL.
    These can be cached forever using the plone.stableResource ruleset.
    """


class IPluggableBinaryFieldValidation(Interface):
    def __call__(field, value):
        """validates field and value.

        raises zope.schema.ValidationError
        returns None
        """


class IPluggableFileFieldValidation(IPluggableBinaryFieldValidation):
    """pluggable validation for binary File fields"""


class IPluggableImageFieldValidation(IPluggableBinaryFieldValidation):
    """pluggable validation for binary Image fields"""


# Values


class INamed(Interface):
    """An item with a filename"""

    filename = schema.TextLine(title="Filename", required=False, default=None)


class INamedTyped(INamed, ITyped):
    """An item with a filename and contentType"""


class INamedFile(INamedTyped, IFile):
    """A non-BLOB file with a filename"""


class INamedImage(INamedTyped, IImage):
    """A non-BLOB image with a filename"""


# Fields


class INamedField(IObject):
    """Base field type"""


class INamedFileField(INamedField):
    """Field for storing INamedFile objects."""

    accept = schema.Tuple(
        title=_("namedfile_accept_title", default="accept types"),
        description=_(
            "namedfile_accept_description",
            default=(
                "The media types which are allowed for this field. "
                "Unset to allow any type. "
                'Can be any valid identifier for the "accept" attribute of '
                'the HTML file input, like extensions (e.g. ".mp3") or IANA '
                'media types (e.g. "image/webp").'
            ),
        ),
        value_type=schema.TextLine(),
        default=(),
        required=False,
    )


class INamedImageField(INamedField):
    """Field for storing INamedImage objects."""

    accept = schema.Tuple(
        title=_("namedimage_accept_title", default="accept types"),
        description=_(
            "namedimage_accept_description",
            default=(
                "The media types which are allowed for this image field. "
                'The default is to allow any "image/*" content type. '
                "Unset to allow any type. "
                'Can be any valid identifier for the "accept" attribute of '
                'the HTML file input, like extensions (e.g. ".jpg") or IANA '
                'media types (e.g. "image/webp").'
            ),
        ),
        value_type=schema.TextLine(),
        default=("image/*",),
        required=False,
    )


class IStorage(Interface):
    """Store file data"""

    def store(data, blob):
        """Store the data into the blob
        Raises NonStorable if data is not storable.
        """


class NotStorable(Exception):
    """Data is not storable"""


# Values


class IBlobby(Interface):
    """Marker interface for objects that support blobs."""


class INamedBlobFile(INamedFile, IBlobby):
    """A BLOB file with a filename"""


class INamedBlobImage(INamedImage, IBlobby):
    """A BLOB image with a filename"""


# Fields


class INamedBlobFileField(INamedFileField):
    """Field for storing INamedBlobFile objects."""


class INamedBlobImageField(INamedImageField):
    """Field for storing INamedBlobImage objects."""
