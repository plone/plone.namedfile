from plone.namedfile import NamedBlobFile
from plone.namedfile import NamedBlobImage
from plone.namedfile import NamedFile
from plone.namedfile import NamedImage
from plone.namedfile.interfaces import INamedBlobFileField
from plone.namedfile.interfaces import INamedBlobImageField
from plone.namedfile.interfaces import INamedFileField
from plone.namedfile.interfaces import INamedImageField
from plone.rfc822.defaultfields import BaseFieldMarshaler
from zope.component import adapter
from zope.interface import Interface


class BaseNamedFileFieldMarshaler(BaseFieldMarshaler):
    """Base marshaler for plone.namedfile values. Actual adapters are
    registered as subclasses.
    """

    ascii = False
    factory = None

    def encode(self, value, charset="utf-8", primary=False):
        # we only support encoding a file value in the body of a message,
        # never in a header
        if not primary:
            raise ValueError(
                "File fields can only be marshaled as primary fields",
            )
        if value is None:
            return None
        return value.data

    def decode(
        self,
        value,
        message=None,
        charset="utf-8",
        contentType=None,
        primary=False,
    ):
        filename = None
        if primary and message is not None:
            filename = message.get_filename(None)
        return self.factory(value, contentType or "", filename)

    def getContentType(self):
        value = self._query()
        if value is None:
            return None
        if not isinstance(value.contentType, str):
            return value.contentType.decode("utf8")
        return value.contentType

    def postProcessMessage(self, message):
        """Encode message as base64 and set content disposition"""
        value = self._query()
        if value is not None:
            filename = value.filename
            if filename:
                message.add_header("Content-Disposition", "attachment")
                message.set_param(
                    "filename",
                    filename,
                    header="Content-Disposition",
                    charset="utf-8",
                )


@adapter(Interface, INamedFileField)
class NamedFileFieldMarshaler(BaseNamedFileFieldMarshaler):
    """Marshaler for an INamedFile field"""

    factory = NamedFile


@adapter(Interface, INamedImageField)
class NamedImageFieldMarshaler(BaseNamedFileFieldMarshaler):
    """Marshaler for an INamedImage field"""

    factory = NamedImage


@adapter(Interface, INamedBlobFileField)
class NamedBlobFileFieldMarshaler(BaseNamedFileFieldMarshaler):
    """Marshaler for an INamedBlobFile field"""

    factory = NamedBlobFile


@adapter(Interface, INamedBlobImageField)
class NamedBlobImageFieldMarshaler(BaseNamedFileFieldMarshaler):
    """Marshaler for an INamedBlobImage field"""

    factory = NamedBlobImage
