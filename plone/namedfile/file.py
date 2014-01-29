# The implementations in this file are largely borrowed
# from zope.app.file and z3c.blobfile
# and are licensed under the ZPL.

import struct
from cStringIO import StringIO

from persistent import Persistent
import transaction

from zope.component import getUtility
from zope.interface import implements
from zope.schema.fieldproperty import FieldProperty

from plone.namedfile.interfaces import INamedFile, INamedImage
from plone.namedfile.utils import get_contenttype

from ZODB.blob import Blob
from plone.namedfile.interfaces import INamedBlobFile, INamedBlobImage
from plone.namedfile.interfaces import IStorage

MAXCHUNKSIZE = 1 << 16
IMAGE_INFO_BYTES = 1024
MAX_INFO_BYTES = 1 << 16


class FileChunk(Persistent):
    """Wrapper for possibly large data"""

    next = None

    def __init__(self, data):
        self._data = data

    def __getslice__(self, i, j):
        return self._data[i:j]

    def __len__(self):
        data = str(self)
        return len(data)

    def __str__(self):
        next = self.next
        if next is None:
            return self._data

        result = [self._data]
        while next is not None:
            self = next
            result.append(self._data)
            next = self.next

        return ''.join(result)


FILECHUNK_CLASSES = [FileChunk]
try:
    from zope.app.file.file import FileChunk as zafFileChunk
    FILECHUNK_CLASSES.append(zafFileChunk)
except ImportError:
    pass


class NamedFile(Persistent):
    """A non-BLOB file that stores a filename

    Let's test the constructor:

    >>> file = NamedFile()
    >>> file.contentType
    ''
    >>> file.data
    ''

    >>> file = NamedFile('Foobar')
    >>> file.contentType
    ''
    >>> file.data
    'Foobar'

    >>> file = NamedFile('Foobar', 'text/plain')
    >>> file.contentType
    'text/plain'
    >>> file.data
    'Foobar'

    >>> file = NamedFile(data='Foobar', contentType='text/plain')
    >>> file.contentType
    'text/plain'
    >>> file.data
    'Foobar'


    Let's test the mutators:

    >>> file = NamedFile()
    >>> file.contentType = 'text/plain'
    >>> file.contentType
    'text/plain'

    >>> file.data = 'Foobar'
    >>> file.data
    'Foobar'

    >>> file.data = None
    Traceback (most recent call last):
    ...
    TypeError: Cannot set None data on a file.


    Let's test large data input:

    >>> file = NamedFile()

    Insert as string:

    >>> file.data = 'Foobar'*60000
    >>> file.getSize()
    360000
    >>> file.data == 'Foobar'*60000
    True

    Insert data as FileChunk:

    >>> fc = FileChunk('Foobar'*4000)
    >>> file.data = fc
    >>> file.getSize()
    24000
    >>> file.data == 'Foobar'*4000
    True

    Insert data from file object:

    >>> import cStringIO
    >>> sio = cStringIO.StringIO()
    >>> sio.write('Foobar'*100000)
    >>> sio.seek(0)
    >>> file.data = sio
    >>> file.getSize()
    600000
    >>> file.data == 'Foobar'*100000
    True


    Last, but not least, verify the interface:

    >>> from zope.interface.verify import verifyClass
    >>> INamedFile.implementedBy(NamedFile)
    True
    >>> verifyClass(INamedFile, NamedFile)
    True
    """
    implements(INamedFile)

    filename = FieldProperty(INamedFile['filename'])

    def __init__(self, data='', contentType='', filename=None):
        if filename is not None and contentType in ('', 'application/octet-stream'):
            contentType = get_contenttype(filename=filename)
        self.data = data
        self.contentType = contentType
        self.filename = filename

    def _getData(self):
        if isinstance(self._data, tuple(FILECHUNK_CLASSES)):
            return str(self._data)
        else:
            return self._data

    def _setData(self, data) :

        # Handle case when data is a string
        if isinstance(data, unicode):
            data = data.encode('UTF-8')

        if isinstance(data, str):
            self._data, self._size = FileChunk(data), len(data)
            return

        # Handle case when data is None
        if data is None:
            raise TypeError('Cannot set None data on a file.')

        # Handle case when data is already a FileChunk
        if isinstance(data, tuple(FILECHUNK_CLASSES)):
            size = len(data)
            self._data, self._size = data, size
            return

        # Handle case when data is a file object
        seek = data.seek
        read = data.read

        seek(0, 2)
        size = end = data.tell()

        if size <= 2*MAXCHUNKSIZE:
            seek(0)
            if size < MAXCHUNKSIZE:
                self._data, self._size = read(size), size
                return
            self._data, self._size = FileChunk(read(size)), size
            return

        # Make sure we have an _p_jar, even if we are a new object, by
        # doing a sub-transaction commit.
        transaction.savepoint(optimistic=True)

        jar = self._p_jar

        if jar is None:
            # Ugh
            seek(0)
            self._data, self._size = FileChunk(read(size)), size
            return

        # Now we're going to build a linked list from back
        # to front to minimize the number of database updates
        # and to allow us to get things out of memory as soon as
        # possible.
        next = None
        while end > 0:
            pos = end - MAXCHUNKSIZE
            if pos < MAXCHUNKSIZE:
                pos = 0 # we always want at least MAXCHUNKSIZE bytes
            seek(pos)
            data = FileChunk(read(end - pos))

            # Woooop Woooop Woooop! This is a trick.
            # We stuff the data directly into our jar to reduce the
            # number of updates necessary.
            jar.add(data)

            # This is needed and has side benefit of getting
            # the thing registered:
            data.next = next

            # Now make it get saved in a sub-transaction!
            transaction.savepoint(optimistic=True)

            # Now make it a ghost to free the memory.  We
            # don't need it anymore!
            data._p_changed = None

            next = data
            end = pos

        self._data, self._size = next, size
        return

    def getSize(self):
        '''See `IFile`'''
        return self._size

    # See IFile.
    data = property(_getData, _setData)


class NamedImage(NamedFile):
    """An non-BLOB image with a filename
    """
    implements(INamedImage)
    filename = FieldProperty(INamedFile['filename'])

    def __init__(self, data='', contentType='', filename=None):
        self.contentType, self._width, self._height = getImageInfo(data)
        self.data = data
        self.filename = filename

        # Allow override of the image sniffer
        if contentType:
            self.contentType = contentType

    def _setData(self, data):
        super(NamedImage, self)._setData(data)

        contentType, self._width, self._height = getImageInfo(self._data)
        if contentType:
            self.contentType = contentType

    def getImageSize(self):
        '''See interface `IImage`'''
        return (self._width, self._height)

    data = property(NamedFile._getData, _setData)


def getImageInfo(data):
    data = str(data)
    size = len(data)
    height = -1
    width = -1
    content_type = ''

    # handle GIFs
    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # Check to see if content_type is correct
        content_type = 'image/gif'
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)

    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif ((size >= 24) and data.startswith('\211PNG\r\n\032\n')
          and (data[12:16] == 'IHDR')):
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[8:16])
        width = int(w)
        height = int(h)

    # handle JPEGs
    elif (size >= 2) and data.startswith('\377\330'):
        content_type = 'image/jpeg'
        jpeg = StringIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            w = -1
            h = -1
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = jpeg.read(1)
                while (ord(b) == 0xFF): b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack(">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0])-2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except struct.error:
            pass
        except ValueError:
            pass
        except TypeError:
            pass

    # handle BMPs
    elif (size >= 30) and data.startswith('BM'):
        kind = struct.unpack("<H", data[14:16])[0]
        if kind == 40: # Windows 3.x bitmap
            content_type = 'image/x-ms-bmp'
            width, height = struct.unpack("<LL", data[18:26])

    return content_type, width, height


class NamedBlobFile(Persistent):
    """A file stored in a ZODB BLOB, with a filename"""
    implements(INamedBlobFile)

    filename = FieldProperty(INamedFile['filename'])

    def __init__(self, data='', contentType='', filename=None):
        if filename is not None and contentType in ('', 'application/octet-stream'):
            contentType = get_contenttype(filename=filename)
        self.contentType = contentType
        self._blob = Blob()
        f = self._blob.open('w')
        f.write('')
        f.close()
        self._setData(data)
        self.filename = filename

    def open(self, mode='r'):
        if mode != 'r' and 'size' in self.__dict__:
            del self.__dict__['size']
        return self._blob.open(mode)

    def openDetached(self):
        return open(self._blob.committed(), 'rb')

    def _setData(self, data):
        if 'size' in self.__dict__:
            del self.__dict__['size']
        # Search for a storable that is able to store the data
        dottedName = ".".join((data.__class__.__module__,
                               data.__class__.__name__))
        storable = getUtility(IStorage, name=dottedName)
        storable.store(data, self._blob)

    def _getData(self):
        fp = self._blob.open('r')
        data = fp.read()
        fp.close()
        return data

    _data = property(_getData, _setData)
    data = property(_getData, _setData)

    @property
    def size(self):
        if 'size' in self.__dict__:
            return self.__dict__['size']
        reader = self._blob.open()
        reader.seek(0,2)
        size = int(reader.tell())
        reader.close()
        self.__dict__['size'] = size
        return size

    def getSize(self):
        return self.size


class NamedBlobImage(NamedBlobFile):
    """An image stored in a ZODB BLOB with a filename
    """
    implements(INamedBlobImage)

    def __init__(self, data='', contentType='', filename=None):
        super(NamedBlobImage, self).__init__(data, filename=filename)

        # Allow override of the image sniffer
        if contentType:
            self.contentType = contentType

    def _setData(self, data):
        super(NamedBlobImage, self)._setData(data)
        firstbytes = self.getFirstBytes()
        res = getImageInfo(firstbytes)
        if res == ('image/jpeg', -1, -1):
            # header was longer than firstbytes
            start = len(firstbytes)
            length = max(0, MAX_INFO_BYTES - start)
            firstbytes += self.getFirstBytes(start, length)
            res = getImageInfo(firstbytes)
        contentType, self._width, self._height = res
        if contentType:
            self.contentType = contentType

    data = property(NamedBlobFile._getData, _setData)

    def getFirstBytes(self, start=0, length=IMAGE_INFO_BYTES):
        """Returns the first bytes of the file.

        Returns an amount which is sufficient to determine the image type.
        """
        fp = self.open('r')
        fp.seek(start)
        firstbytes = fp.read(length)
        fp.close()
        return firstbytes

    def getImageSize(self):
        """See interface `IImage`"""
        return (self._width, self._height)
