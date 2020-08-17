Usage
=====

This demonstrates how to use the package.

Schema fields
-------------

The following schema fields can be used to describe file data. We'll only
test the BLOB versions of the fields if z3c.blobfile is installed::

    >>> from zope.interface import Interface
    >>> from plone.namedfile import field

    >>> class IFileContainer(Interface):
    ...     simple = field.NamedFile(title=u"Named file")
    ...     image = field.NamedImage(title=u"Named image file")
    ...     blob = field.NamedBlobFile(title=u"Named blob file")
    ...     blobimage = field.NamedBlobImage(title=u"Named blob image file")

These store data with the following types::

    >>> from zope.interface import implementer
    >>> from plone import namedfile


    >>> @implementer(IFileContainer)
    ... class FileContainer(object):
    ...     __allow_access_to_unprotected_subobjects__ = 1
    ...     def __init__(self):
    ...         self.simple = namedfile.NamedFile()
    ...         self.image = namedfile.NamedImage()
    ...         self.blob = namedfile.NamedBlobFile()
    ...         self.blobimage = namedfile.NamedBlobImage()


File data and content type
--------------------------

Let's now show how to get and set file data.

The FileContainer class creates empty objects to start with::

    >>> container = FileContainer()

    >>> container.simple.data
    ''
    >>> container.simple.contentType
    ''
    >>> container.simple.filename is None
    True

    >>> container.image.data
    ''
    >>> container.image.contentType
    ''
    >>> container.image.filename is None
    True

    >>> container.blob.data
    ''
    >>> container.blob.contentType
    ''
    >>> container.blob.filename is None
    True
    >>> container.blobimage.data
    ''
    >>> container.blobimage.contentType
    ''
    >>> container.blobimage.filename is None
    True

Let's now set some actual data in these files. Notice how the constructor
will attempt to guess the filename from the file extension::

    >>> container.simple = namedfile.NamedFile('dummy test data', filename=u"test.txt")
    >>> container.simple.data
    'dummy test data'
    >>> container.simple.contentType
    'text/plain'
    >>> container.simple.filename
    u'test.txt'

    >>> container.blob = namedfile.NamedBlobFile('dummy test data', filename=u"test.txt")
    >>> container.blob.data
    'dummy test data'
    >>> container.blob.contentType
    'text/plain'
    >>> container.blob.filename
    u'test.txt'

Let's also try to read a GIF, courtesy of the zope.app.file tests::

    >>> zptlogo = (
    ...     'GIF89a\x10\x00\x10\x00\xd5\x00\x00\xff\xff\xff\xff\xff\xfe\xfc\xfd\xfd'
    ...     '\xfa\xfb\xfc\xf7\xf9\xfa\xf5\xf8\xf9\xf3\xf6\xf8\xf2\xf5\xf7\xf0\xf4\xf6'
    ...     '\xeb\xf1\xf3\xe5\xed\xef\xde\xe8\xeb\xdc\xe6\xea\xd9\xe4\xe8\xd7\xe2\xe6'
    ...     '\xd2\xdf\xe3\xd0\xdd\xe3\xcd\xdc\xe1\xcb\xda\xdf\xc9\xd9\xdf\xc8\xd8\xdd'
    ...     '\xc6\xd7\xdc\xc4\xd6\xdc\xc3\xd4\xda\xc2\xd3\xd9\xc1\xd3\xd9\xc0\xd2\xd9'
    ...     '\xbd\xd1\xd8\xbd\xd0\xd7\xbc\xcf\xd7\xbb\xcf\xd6\xbb\xce\xd5\xb9\xcd\xd4'
    ...     '\xb6\xcc\xd4\xb6\xcb\xd3\xb5\xcb\xd2\xb4\xca\xd1\xb2\xc8\xd0\xb1\xc7\xd0'
    ...     '\xb0\xc7\xcf\xaf\xc6\xce\xae\xc4\xce\xad\xc4\xcd\xab\xc3\xcc\xa9\xc2\xcb'
    ...     '\xa8\xc1\xca\xa6\xc0\xc9\xa4\xbe\xc8\xa2\xbd\xc7\xa0\xbb\xc5\x9e\xba\xc4'
    ...     '\x9b\xbf\xcc\x98\xb6\xc1\x8d\xae\xbaFgs\x00\x00\x00\x00\x00\x00\x00\x00'
    ...     '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    ...     '\x00,\x00\x00\x00\x00\x10\x00\x10\x00\x00\x06z@\x80pH,\x12k\xc8$\xd2f\x04'
    ...     '\xd4\x84\x01\x01\xe1\xf0d\x16\x9f\x80A\x01\x91\xc0ZmL\xb0\xcd\x00V\xd4'
    ...     '\xc4a\x87z\xed\xb0-\x1a\xb3\xb8\x95\xbdf8\x1e\x11\xca,MoC$\x15\x18{'
    ...     '\x006}m\x13\x16\x1a\x1f\x83\x85}6\x17\x1b $\x83\x00\x86\x19\x1d!%)\x8c'
    ...     '\x866#\'+.\x8ca`\x1c`(,/1\x94B5\x19\x1e"&*-024\xacNq\xba\xbb\xb8h\xbeb'
    ...     '\x00A\x00;'
    ...     )

    >>> container.image = namedfile.NamedImage(zptlogo, filename=u"zpt.gif")
    >>> container.image.data == zptlogo
    True
    >>> container.image.contentType
    'image/gif'
    >>> container.image.filename
    u'zpt.gif'

    >>> container.blobimage = namedfile.NamedBlobImage(zptlogo, filename=u"zpt.gif")
    >>> container.blobimage.data == zptlogo
    True
    >>> container.blobimage.contentType
    'image/gif'
    >>> container.blobimage.filename
    u'zpt.gif'

Note that is possible for force the mimetype::

    >>> container.image = namedfile.NamedImage(zptlogo, contentType='image/foo', filename=u"zpt.gif")
    >>> container.image.data == zptlogo
    True
    >>> container.image.contentType
    'image/foo'
    >>> container.image.filename
    u'zpt.gif'

    >>> container.blobimage = namedfile.NamedBlobImage(zptlogo, contentType='image/foo', filename=u"zpt.gif")
    >>> container.blobimage.data == zptlogo
    True
    >>> container.blobimage.contentType
    'image/foo'
    >>> container.blobimage.filename
    u'zpt.gif'

The filename must be set to a unicode string, not a bytestring::

    >>> container.image.filename = 'foo'
    Traceback (most recent call last):
    ...
    WrongType: ('foo', <type 'unicode'>, 'filename')


Download view
-------------

This package also comes with a view that can be used to download files. This
will set Content-Disposition to ensure the browser downloads the file rather
than displaying it. To use it, link to ../context-object/@@download/fieldname,
where `fieldname` is the name of the attribute on the context-object where the
named file is stored.

We will test this with a dummy request, faking traversal::

    >>> from plone.namedfile.browser import Download
    >>> from zope.publisher.browser import TestRequest

    >>> request = TestRequest()
    >>> download = Download(container, request).publishTraverse(request, 'simple')
    >>> download()
    'dummy test data'
    >>> request.response.getHeader('Content-Length')
    '15'
    >>> request.response.getHeader('Content-Type')
    'text/plain'
    >>> request.response.getHeader('Content-Disposition')
    "attachment; filename*=UTF-8''test.txt"

    >>> request = TestRequest()
    >>> download = Download(container, request).publishTraverse(request, 'blob')
    >>> data = download()
    >>> hasattr(data, 'read') and data.read() or data
    'dummy test data'
    >>> request.response.getHeader('Content-Length')
    '15'
    >>> request.response.getHeader('Content-Type')
    'text/plain'
    >>> request.response.getHeader('Content-Disposition')
    "attachment; filename*=UTF-8''test.txt"

    >>> request = TestRequest()
    >>> download = Download(container, request).publishTraverse(request, 'image')
    >>> download() == zptlogo
    True

    >>> request.response.getHeader('Content-Length')
    '341'
    >>> request.response.getHeader('Content-Type')
    'image/foo'
    >>> request.response.getHeader('Content-Disposition')
    "attachment; filename*=UTF-8''zpt.gif"

    >>> request = TestRequest()
    >>> download = Download(container, request).publishTraverse(request, 'blobimage')
    >>> data = download()
    >>> (hasattr(data, 'read') and data.read() or data) == zptlogo
    True
    >>> request.response.getHeader('Content-Length')
    '341'
    >>> request.response.getHeader('Content-Type')
    'image/foo'
    >>> request.response.getHeader('Content-Disposition')
    "attachment; filename*=UTF-8''zpt.gif"


Display-file view
-----------------

This package also comes with a view that can be used to display files in the
browser. To use it, link to ../context-object/@@display-file/fieldname, where
`fieldname` is the name of the attribute on the context-object where the named
file is stored.

We will test this with a dummy request, faking traversal::

    >>> from plone.namedfile.browser import DisplayFile
    >>> from zope.publisher.browser import TestRequest

    >>> request = TestRequest()
    >>> display_file = DisplayFile(container, request).publishTraverse(request, 'simple')
    >>> display_file()
    'dummy test data'
    >>> request.response.getHeader('Content-Length')
    '15'
    >>> request.response.getHeader('Content-Type')
    'text/plain'
    >>> request.response.getHeader('Content-Disposition')

    >>> request = TestRequest()
    >>> display_file = DisplayFile(container, request).publishTraverse(request, 'blob')
    >>> data = display_file()
    >>> hasattr(data, 'read') and data.read() or data
    'dummy test data'
    >>> request.response.getHeader('Content-Length')
    '15'
    >>> request.response.getHeader('Content-Type')
    'text/plain'
    >>> request.response.getHeader('Content-Disposition')

    >>> request = TestRequest()
    >>> display_file = DisplayFile(container, request).publishTraverse(request, 'image')
    >>> display_file() == zptlogo
    True

    >>> request.response.getHeader('Content-Length')
    '341'
    >>> request.response.getHeader('Content-Type')
    'image/foo'
    >>> request.response.getHeader('Content-Disposition')

    >>> request = TestRequest()
    >>> display_file = DisplayFile(container, request).publishTraverse(request, 'blobimage')
    >>> data = display_file()
    >>> (hasattr(data, 'read') and data.read() or data) == zptlogo
    True
    >>> request.response.getHeader('Content-Length')
    '341'
    >>> request.response.getHeader('Content-Type')
    'image/foo'
    >>> request.response.getHeader('Content-Disposition')


Specifying the primary field
----------------------------

To use the @@download view without specifying the field in the URL, the
primary field information must be registered with an adapter. (Frameworks such
as plone.dexterity may already have done this for you.)::

    >>> from plone.rfc822.interfaces import IPrimaryFieldInfo
    >>> from zope.component import adapter

    >>> @implementer(IPrimaryFieldInfo)
    ... @adapter(IFileContainer)
    ... class FieldContainerPrimaryFieldInfo(object):
    ...     fieldname = 'simple'
    ...     field = IFileContainer['simple']
    ...     def __init__(self, context):
    ...         self.value = context.simple

    >>> from zope.component import getSiteManager
    >>> components = getSiteManager()
    >>> components.registerAdapter(FieldContainerPrimaryFieldInfo)

We will test this with a dummy request, faking traversal::

    >>> request = TestRequest()
    >>> download = Download(container, request)
    >>> download()
    'dummy test data'
    >>> request.response.getHeader('Content-Length')
    '15'
    >>> request.response.getHeader('Content-Type')
    'text/plain'
    >>> request.response.getHeader('Content-Disposition')
    "attachment; filename*=UTF-8''test.txt"


Image scales
------------

This package can handle the creation, storage, and retrieval of arbitrarily
sized scaled versions of images stored in NamedImage or NamedBlobImage fields.

Image scales are accessed via an @@images view that is available for any item
providing ``plone.namedfile.interfaces.IImageScaleTraversable``.  There are
several ways that you may reference scales from page templates.

1. for full control you may do the tag generation explicitly::

     <img tal:define="scales context/@@images;
                      thumbnail python: scales.scale('image', width=64, height=64);"
          tal:condition="thumbnail"
          tal:attributes="src thumbnail/url;
                          width thumbnail/width;
                          height thumbnail/height" />

   This would create an up to 64 by 64 pixel scaled down version of the image
   stored in the "image" field.  It also allows for passing in additional
   parameters support by `plone.scale`_'s ``scaleImage`` function, e.g.
   ``direction`` or ``quality``.

   .. _`plone.scale`: http://pypi.python.org/pypi/plone.scale

2. for automatic tag generation with extra parameters you would use::

     <img tal:define="scale context/@@images"
          tal:replace="structure python: scale.scale('image',
                       width=1200, height=800, direction='down').tag()" />

3. It is possible to access scales via predefined named scale sizes, rather
   than hardcoding the dimensions every time you access a scale.  The scale
   sizes are found via calling a utility providing
   ``plone.namedfile.interfaces.IAvailableSizes``, which should return a dict of
   scale name => (width, height).  A scale called 'mini' could then be accessed
   like this::

     <img tal:define="scale context/@@images"
          tal:replace="structure python: scale.scale('image',
                       scale='mini').tag()" />

   This would use the predefined scale size "mini" to determine the desired
   image dimensions, but still allow to pass in extra parameters.

4. a convenience short-cut for option 3 can be used::

     <img tal:replace="structure context/@@images/image/mini" />

5. and lastly, the short-cut can also be used to render the unscaled image::

     <img tal:replace="structure context/@@images/image" />
