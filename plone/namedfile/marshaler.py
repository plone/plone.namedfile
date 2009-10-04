from plone.namedfile.interfaces import HAVE_BLOBS

try:
    from plone.rfc822.defaultfields import BaseFieldMarshaler
    HAVE_MARSHALER = True
except ImportError:
    HAVE_MARSHALER = False

if HAVE_MARSHALER:

    from email.Encoders import encode_base64

    from zope.interface import Interface
    from zope.component import adapts

    from plone.namedfile.interfaces import INamedFileField
    from plone.namedfile.interfaces import INamedImageField
    
    from plone.namedfile import NamedFile, NamedImage
    
    class BaseNamedFileFieldMarshaler(BaseFieldMarshaler):
        """Base marshaler for plone.namedfile values. Actual adapters are
        registered as subclasses.
        """
    
        ascii = False
        factory = None
    
        def encode(self, value, charset='utf-8', primary=False):
            # we only support encoding a file value in the body of a message,
            # never in a header
            if not primary:
                raise ValueError("File fields can only be marshaled as primary fields")
            if value is None:
                return None
            return value.data
            
        def decode(self, value, message=None, charset='utf-8', contentType=None, primary=False):
            filename = None
            if primary and message is not None:
                filename = message.get_filename(None)
            return self.factory(value, contentType or '', filename)

        def getContentType(self):
            value = self._query()
            if value is None:
                return None
            return value.contentType
        
        def getCharset(self, default='utf-8'):
            return None
        
        def postProcessMessage(self, message):
            """Encode message as base64 and set content disposition
            """
            value = self._query()
            if value is not None:
                filename = value.filename
                if filename:
                    message.add_header('Content-Disposition', 'attachment', filename=filename)
            
            encode_base64(message)
        
    class NamedFileFieldMarshaler(BaseNamedFileFieldMarshaler):
        """Marshaler for an INamedFile field
        """
        
        adapts(Interface, INamedFileField)
        factory = NamedFile

    class NamedImageFieldMarshaler(BaseNamedFileFieldMarshaler):
        """Marshaler for an INamedImage field
        """
        
        adapts(Interface, INamedImageField)
        factory = NamedImage

if HAVE_MARSHALER and HAVE_BLOBS:
    
    from plone.namedfile.interfaces import INamedBlobFileField
    from plone.namedfile.interfaces import INamedBlobImageField
    
    from plone.namedfile import NamedBlobFile, NamedBlobImage
    
    class NamedBlobFileFieldMarshaler(BaseNamedFileFieldMarshaler):
        """Marshaler for an INamedBlobFile field
        """
        
        adapts(Interface, INamedBlobFileField)
        factory = NamedBlobFile

    class NamedBlobImageFieldMarshaler(BaseNamedFileFieldMarshaler):
        """Marshaler for an INamedBlobImage field
        """
        
        adapts(Interface, INamedBlobImageField)
        factory = NamedBlobImage
