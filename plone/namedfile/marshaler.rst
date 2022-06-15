plone.rfc822 marshaler
======================

This package includes a field marshaler for ``plone.rfc822``, which will be
installed if that package is installed.

To test this, we must first load some configuration::

    >>> configuration = """\
    ... <configure
    ...      xmlns="http://namespaces.zope.org/zope"
    ...      i18n_domain="plone.namedfile.tests">
    ...
    ...     <include package="zope.component" file="meta.zcml" />
    ...     <include package="zope.security" file="meta.zcml" />
    ...
    ...     <include package="plone.rfc822" />
    ...
    ...     <include package="plone.namedfile" file="marshaler.zcml" />
    ...
    ... </configure>
    ... """

    >>> import io
    >>> from zope.configuration import xmlconfig
    >>> xmlconfig.xmlconfig(io.StringIO(configuration))

Next, we will create a schema with which to test the marshaler::

    >>> from zope.interface import Interface
    >>> from plone.namedfile import field

    >>> class ITestContent(Interface):
    ...     _file = field.NamedFile()
    ...     _image = field.NamedImage()

We'll create an instance with some data, too::

    >>> from plone.namedfile import NamedFile, NamedImage
    >>> fileValue = NamedFile('dummy test data', 'text/plain', filename=u"test.txt")
    >>> zptlogo = (
    ...     b'GIF89a\x10\x00\x10\x00\xd5\x00\x00\xff\xff\xff\xff\xff\xfe\xfc\xfd\xfd'
    ...     b'\xfa\xfb\xfc\xf7\xf9\xfa\xf5\xf8\xf9\xf3\xf6\xf8\xf2\xf5\xf7\xf0\xf4\xf6'
    ...     b'\xeb\xf1\xf3\xe5\xed\xef\xde\xe8\xeb\xdc\xe6\xea\xd9\xe4\xe8\xd7\xe2\xe6'
    ...     b'\xd2\xdf\xe3\xd0\xdd\xe3\xcd\xdc\xe1\xcb\xda\xdf\xc9\xd9\xdf\xc8\xd8\xdd'
    ...     b'\xc6\xd7\xdc\xc4\xd6\xdc\xc3\xd4\xda\xc2\xd3\xd9\xc1\xd3\xd9\xc0\xd2\xd9'
    ...     b'\xbd\xd1\xd8\xbd\xd0\xd7\xbc\xcf\xd7\xbb\xcf\xd6\xbb\xce\xd5\xb9\xcd\xd4'
    ...     b'\xb6\xcc\xd4\xb6\xcb\xd3\xb5\xcb\xd2\xb4\xca\xd1\xb2\xc8\xd0\xb1\xc7\xd0'
    ...     b'\xb0\xc7\xcf\xaf\xc6\xce\xae\xc4\xce\xad\xc4\xcd\xab\xc3\xcc\xa9\xc2\xcb'
    ...     b'\xa8\xc1\xca\xa6\xc0\xc9\xa4\xbe\xc8\xa2\xbd\xc7\xa0\xbb\xc5\x9e\xba\xc4'
    ...     b'\x9b\xbf\xcc\x98\xb6\xc1\x8d\xae\xbaFgs\x00\x00\x00\x00\x00\x00\x00\x00'
    ...     b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    ...     b'\x00,\x00\x00\x00\x00\x10\x00\x10\x00\x00\x06z@\x80pH,\x12k\xc8$\xd2f\x04'
    ...     b'\xd4\x84\x01\x01\xe1\xf0d\x16\x9f\x80A\x01\x91\xc0ZmL\xb0\xcd\x00V\xd4'
    ...     b'\xc4a\x87z\xed\xb0-\x1a\xb3\xb8\x95\xbdf8\x1e\x11\xca,MoC$\x15\x18{'
    ...     b'\x006}m\x13\x16\x1a\x1f\x83\x85}6\x17\x1b $\x83\x00\x86\x19\x1d!%)\x8c'
    ...     b'\x866#\'+.\x8ca`\x1c`(,/1\x94B5\x19\x1e"&*-024\xacNq\xba\xbb\xb8h\xbeb'
    ...     b'\x00A\x00;'
    ...     )
    >>> imageValue = NamedImage(zptlogo, 'image/gif', filename=u'zptl\xf8go.gif')

    >>> from zope.interface import implementer
    >>> @implementer(ITestContent)
    ... class TestContent(object):
    ...     _file = None
    ...     _image = None

    >>> t = TestContent()
    >>> t._file = fileValue
    >>> t._image = imageValue

We can now look up and test the marshaler::

    >>> from zope.component import getMultiAdapter
    >>> from plone.rfc822.interfaces import IFieldMarshaler

For the moment, fields are not marked as primary. Our marshaller will refuse
to marshal a non-primary field, as it does not make much sense to encode
binary data into a UTF-8 string in a header::

    >>> marshaler = getMultiAdapter((t, ITestContent['_file']), IFieldMarshaler)
    >>> marshaler.marshal()
    Traceback (most recent call last):
    ...
    ValueError: File fields can only be marshaled as primary fields

    >>> marshaler.getContentType()
    'text/plain'

    >>> marshaler.ascii
    False

    >>> marshaler = getMultiAdapter((t, ITestContent['_image']), IFieldMarshaler)
    >>> marshaler.marshal() is None
    Traceback (most recent call last):
    ...
    ValueError: File fields can only be marshaled as primary fields

    >>> marshaler.getContentType()
    'image/gif'

    >>> marshaler.ascii
    False

Let's try it with primary fields::

    >>> marshaler = getMultiAdapter((t, ITestContent['_file']), IFieldMarshaler)
    >>> bytearray(marshaler.marshal(primary=True))
    bytearray(b'dummy test data')

    >>> marshaler.getContentType()
    'text/plain'
    >>> marshaler.getCharset('utf-8') is None
    True
    >>> marshaler.ascii
    False

    >>> marshaler = getMultiAdapter((t, ITestContent['_image']), IFieldMarshaler)
    >>> marshaler.marshal(primary=True) == zptlogo
    True

    >>> marshaler.getContentType()
    'image/gif'
    >>> marshaler.getCharset('utf-8') is None
    True
    >>> marshaler.ascii
    False

This marshaler will also post-process a message to encode the filename in the Content-Disposition header.
To illustrate that, as well as parsing of the message,
let's construct a full message and look at the output.

First, we need to mark one of the fields as primary.
In this case, we will use the file field.
The image will will now be ignored, since our marshaler refuses to encode non-primary fields::

    >>> from plone.rfc822.interfaces import IPrimaryField
    >>> from zope.interface import alsoProvides
    >>> alsoProvides(ITestContent['_file'], IPrimaryField)

    >>> from plone.rfc822 import constructMessageFromSchema
    >>> message = constructMessageFromSchema(t, ITestContent)
    >>> messageBody = message.as_string()
    >>> print(messageBody) # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    MIME-Version: 1.0
    Content-Type: text/plain
    Content-Transfer-Encoding: base64
    Content-Disposition: attachment; filename*=utf-8''test.txt
    <BLANKLINE>
    ZHVtbXkgdGVzdCBkYXRh...

You can see here that we have a transfer encoding and a content disposition.

Let's now use this message to construct a new object::

    >>> from email import message_from_string
    >>> inputMessage = message_from_string(messageBody)

    >>> newContent = TestContent()

    >>> from plone.rfc822 import initializeObjectFromSchema
    >>> initializeObjectFromSchema(newContent, ITestContent, inputMessage)
    >>> bytearray(newContent._file.data)
    bytearray(b'dummy test data')
    >>> newContent._file.contentType
    'text/plain'
    >>> newContent._file.filename
    'test.txt'

    >>> newContent._image is None
    True

If we have two primary fields, they will be encoded as a multipart message::

    >>> alsoProvides(ITestContent['_image'], IPrimaryField)
    >>> message = constructMessageFromSchema(t, ITestContent)
    >>> messageBody = message.as_string()
    >>> print(messageBody) # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="===============...=="
    <BLANKLINE>
    --===============...==
    MIME-Version: 1.0
    Content-Type: text/plain
    Content-Transfer-Encoding: base64
    Content-Disposition: attachment; filename*=...utf-8''test.txt...
    <BLANKLINE>
    ZHVtbXkgdGVzdCBkYXRh...
    --===============...==
    MIME-Version: 1.0
    Content-Type: image/gif
    Content-Transfer-Encoding: base64
    Content-Disposition: attachment; filename*=...utf-8''zptl%C3%B8go.gif...
    <BLANKLINE>
    R0lGODlhEAAQANUAAP///////vz9/fr7/Pf5+vX4+fP2+PL19/D09uvx8+Xt797o69zm6tnk6Nfi
    5tLf49Dd483c4cva38nZ38jY3cbX3MTW3MPU2sLT2cHT2cDS2b3R2L3Q17zP17vP1rvO1bnN1LbM
    1LbL07XL0rTK0bLI0LHH0LDHz6/Gzq7Ezq3EzavDzKnCy6jByqbAyaS+yKK9x6C7xZ66xJu/zJi2
    wY2uukZncwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAEAAQAAAGekCAcEgsEmvIJNJm
    BNSEAQHh8GQWn4BBAZHAWm1MsM0AVtTEYYd67bAtGrO4lb1mOB4RyixNb0MkFRh7ADZ9bRMWGh+D
    hX02FxsgJIMAhhkdISUpjIY2IycrLoxhYBxgKCwvMZRCNRkeIiYqLTAyNKxOcbq7uGi+YgBBADs=...
    --===============...==--
    <BLANKLINE>


Of course, we will also be able to load this data from a message::

    >>> inputMessage = message_from_string(messageBody)
    >>> newContent = TestContent()
    >>> initializeObjectFromSchema(newContent, ITestContent, inputMessage)

    >>> bytearray(newContent._file.data)
    bytearray(b'dummy test data')
    >>> newContent._file.contentType
    'text/plain'
    >>> newContent._file.filename
    'test.txt'

    >>> newContent._image.data == zptlogo
    True
    >>> newContent._image.contentType
    'image/gif'
    >>> newContent._image.filename
    'zptl\xf8go.gif'
