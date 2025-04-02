# The implementations in this file are largely borrowed
# from zope.app.file and z3c.blobfile
# and are licensed under the ZPL.
from DateTime import DateTime
from logging import getLogger
from persistent import Persistent
from plone.namedfile.interfaces import INamedBlobFile
from plone.namedfile.interfaces import INamedBlobImage
from plone.namedfile.interfaces import INamedFile
from plone.namedfile.interfaces import INamedImage
from plone.namedfile.interfaces import IStorage
from plone.namedfile.utils import get_contenttype
from plone.namedfile.utils import get_exif
from plone.namedfile.utils import getImageInfo
from plone.namedfile.utils import rotate_image
from ZODB.blob import Blob
from zope.component import getUtility
from zope.interface import implementer
from zope.schema.fieldproperty import FieldProperty
from ZPublisher import HTTPRangeSupport

import piexif
import transaction


log = getLogger(__name__)


MAXCHUNKSIZE = 1 << 16
IMAGE_INFO_BYTES = 1024
MAX_INFO_BYTES = 1 << 18


class FileChunk(Persistent):
    """Wrapper for possibly large data"""

    next = None

    def __init__(self, data):
        self._data = data

    def __getslice__(self, i, j):
        return self._data[i:j]

    def __len__(self):
        data = bytes(self)
        return len(data)

    def _get_contents(self):
        next = self.next
        if next is None:
            return self._data

        result = [self._data]
        while next is not None:
            self = next
            result.append(self._data)
            next = self.next

        return b"".join(result)

    __bytes__ = _get_contents


FILECHUNK_CLASSES = [FileChunk]
try:
    from zope.app.file.file import FileChunk as zafFileChunk

    FILECHUNK_CLASSES.append(zafFileChunk)
except ImportError:
    pass


class ModifiedPropertyMixin:
    @property
    def modified(self):
        if hasattr(self, "_modified"):
            return self._modified / 1000
        # Fall back to modification time in database.
        return self._p_mtime


@implementer(INamedFile)
class NamedFile(Persistent, ModifiedPropertyMixin):
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

    >>> from io import StringIO
    >>> sio = StringIO()
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

    filename = FieldProperty(INamedFile["filename"])

    def __init__(self, data=b"", contentType="", filename=None):
        if filename is not None and contentType in ("", "application/octet-stream"):
            contentType = get_contenttype(filename=filename)
        self.data = data
        self.contentType = contentType
        self.filename = filename
        self._modified = DateTime().millis()

    def _getData(self):
        if isinstance(self._data, tuple(FILECHUNK_CLASSES)):
            return bytes(self._data)
        else:
            return self._data

    def _setData(self, data):
        self._modified = DateTime().millis()

        # Handle case when data is a string
        if isinstance(data, str):
            data = data.encode("UTF-8")

        if isinstance(data, bytes):
            self._data, self._size = FileChunk(data), len(data)
            return

        # Handle case when data is None
        if data is None:
            raise TypeError("Cannot set None data on a file.")

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

        if size <= 2 * MAXCHUNKSIZE:
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
                pos = 0  # we always want at least MAXCHUNKSIZE bytes
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
        """See `IFile`"""
        return self._size

    # See IFile.
    data = property(_getData, _setData)


@implementer(INamedImage)
class NamedImage(NamedFile):
    """An non-BLOB image with a filename"""

    filename = FieldProperty(INamedFile["filename"])

    def __init__(self, data=b"", contentType="", filename=None):
        self.contentType, self._width, self._height = getImageInfo(data)
        self.filename = filename
        self._setData(data)

        # Allow override of the image sniffer
        if contentType:
            self.contentType = contentType

        exif_data = get_exif(data)
        if exif_data is not None:
            log.debug(
                "Image contains Exif Information. "
                "Test for Image Orientation and Rotate if necessary."
                "Exif Data: %s",
                exif_data,
            )
            orientation = exif_data["0th"].get(piexif.ImageIFD.Orientation, 1)
            if 1 < orientation <= 8:
                self.data, self._width, self._height, self.exif = rotate_image(
                    self.data
                )
            self.exif_data = exif_data

    def _setData(self, data):
        super()._setData(data)

        contentType, self._width, self._height = getImageInfo(self._data)
        if contentType:
            self.contentType = contentType

    def getImageSize(self):
        """See interface `IImage`"""
        return (self._width, self._height)

    data = property(NamedFile._getData, _setData)


@implementer(INamedBlobFile, HTTPRangeSupport.HTTPRangeInterface)
class NamedBlobFile(Persistent, ModifiedPropertyMixin):
    """A file stored in a ZODB BLOB, with a filename"""

    filename = FieldProperty(INamedFile["filename"])

    def __init__(self, data=b"", contentType="", filename=None):
        if filename is not None and contentType in ("", "application/octet-stream"):
            contentType = get_contenttype(filename=filename)
        self.contentType = contentType
        self._blob = Blob()
        f = self._blob.open("w")
        f.write(b"")
        f.close()
        self._setData(data)
        self.filename = filename
        self._modified = DateTime().millis()

    def open(self, mode="r"):
        if mode != "r" and "size" in self.__dict__:
            del self.__dict__["size"]
        return self._blob.open(mode)

    def openDetached(self):
        return open(self._blob.committed(), "rb")

    def _setData(self, data):
        if "size" in self.__dict__:
            del self.__dict__["size"]
        # Search for a storable that is able to store the data
        dottedName = ".".join((data.__class__.__module__, data.__class__.__name__))
        log.debug("Storage selected for data: %s", dottedName)
        storable = getUtility(IStorage, name=dottedName)
        storable.store(data, self._blob)
        self._modified = DateTime().millis()

    def _getData(self):
        fp = self._blob.open("r")
        data = fp.read()
        fp.close()
        return data

    _data = property(_getData, _setData)
    data = property(_getData, _setData)

    @property
    def size(self):
        if "size" in self.__dict__:
            return self.__dict__["size"]
        with self._blob.open() as reader:
            reader.seek(0, 2)
            size = int(reader.tell())
        self.__dict__["size"] = size
        return size

    def getSize(self):
        return self.size


@implementer(INamedBlobImage)
class NamedBlobImage(NamedBlobFile):
    """An image stored in a ZODB BLOB with a filename"""

    def __init__(self, data=b"", contentType="", filename=None):
        super().__init__(data, contentType=contentType, filename=filename)

        # Allow override of the image sniffer
        if contentType:
            self.contentType = contentType
        with self.open("r") as fp:
            exif_data = get_exif(fp, self.contentType, self._width, self._height)
        if exif_data is not None:
            log.debug(
                "Image contains Exif Information. "
                "Test for Image Orientation and Rotate if necessary."
                "Exif Data: %s",
                exif_data,
            )
            orientation = exif_data["0th"].get(piexif.ImageIFD.Orientation, 1)
            if 1 < orientation <= 8:
                try:
                    self.data, self._width, self._height, self.exif = rotate_image(
                        self.data
                    )
                except KeyboardInterrupt:
                    raise
                except Exception:
                    log.warning(
                        "Error rotating image %s based on exif data.",
                        filename,
                        exc_info=1,
                    )
            else:
                self.exif = exif_data

    def _setData(self, data):
        super()._setData(data)
        firstbytes = self.getFirstBytes()
        res = getImageInfo(firstbytes)
        if (
            res == ("image/jpeg", -1, -1)
            or res == ("image/tiff", -1, -1)
            or res == ("image/svg+xml", -1, -1)
        ):
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
        with self.open("r") as fp:
            fp.seek(start)
            firstbytes = fp.read(length)
        return firstbytes

    def getImageSize(self):
        """See interface `IImage`"""
        if (self._width, self._height) != (-1, -1):
            return (self._width, self._height)

        contentType, self._width, self._height = getImageInfo(self.data)
        return (self._width, self._height)
