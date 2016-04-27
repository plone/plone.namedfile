# -*- coding: utf-8 -*-

from logging import getLogger
from plone.namedfile.interfaces import IBlobby
from StringIO import StringIO
from ZPublisher.HTTPRequest import FileUpload

import mimetypes
import os.path
import piexif
import PIL.Image
import struct
import urllib


log = getLogger(__name__)


try:
    # use this to stream data if we can
    from ZPublisher.Iterators import filestream_iterator
except ImportError:
    filestream_iterator = None


def safe_basename(filename):
    """Get the basename of the given filename, regardless of which platform
    (Windows or Unix) it originated from.
    """
    fslice = max(
        filename.rfind('/'),
        filename.rfind('\\'),
        filename.rfind(':'),
    ) + 1
    return filename[fslice:]


def get_contenttype(
        file=None,
        filename=None,
        default='application/octet-stream'):
    """Get the MIME content type of the given file and/or filename.
    """

    file_type = getattr(file, 'contentType', None)
    if file_type:
        return file_type

    filename = getattr(file, 'filename', filename)
    if filename:
        extension = os.path.splitext(filename)[1].lower()
        return mimetypes.types_map.get(extension, 'application/octet-stream')

    return default


def set_headers(file, response, filename=None):
    """Set response headers for the given file. If filename is given, set
    the Content-Disposition to attachment.
    """

    contenttype = get_contenttype(file)

    response.setHeader('Content-Type', contenttype)
    response.setHeader('Content-Length', file.getSize())

    if filename is not None:
        if not isinstance(filename, unicode):
            filename = unicode(filename, 'utf-8', errors='ignore')
        filename = urllib.quote(filename.encode('utf8'))
        response.setHeader(
            'Content-Disposition',
            'attachment; filename*=UTF-8\'\'{0}'.format(filename)
        )


def stream_data(file):
    """Return the given file as a stream if possible.
    """

    if IBlobby.providedBy(file) and filestream_iterator is not None:
        # XXX: we may want to use this instead, which would raise an error
        # in case of uncomitted changes
        # filename = file._blob.committed()

        filename = file._blob._p_blob_uncommitted or file._blob.committed()
        return filestream_iterator(filename, 'rb')

    return file.data


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
        w, h = struct.unpack('<HH', data[6:10])
        width = int(w)
        height = int(h)

    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif (
        (size >= 24) and data.startswith('\211PNG\r\n\032\n') and
        (data[12:16] == 'IHDR')
    ):
        content_type = 'image/png'
        w, h = struct.unpack('>LL', data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack('>LL', data[8:16])
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
                while (ord(b) != 0xFF):
                    b = jpeg.read(1)
                while (ord(b) == 0xFF):
                    b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack('>HH', jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack('>H', jpeg.read(2))[0]) - 2)
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
        kind = struct.unpack('<H', data[14:16])[0]
        if kind == 40:  # Windows 3.x bitmap
            content_type = 'image/x-ms-bmp'
            width, height = struct.unpack('<LL', data[18:26])

    # TODO: Tiff Images

    return content_type, width, height


def get_exif(image):
    contenttype = None
    width = None
    height = None
    exif_data = None
    data = str(image)
    contenttype, width, height = getImageInfo(data)
    if contenttype in ['image/jpeg', 'image/tiff']:
        # Only this two Image Types could have Exif informations
        # see http://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf
        try:
            if getattr(image, 'read', None):
                exif_data = piexif.load(image.read())
            else:
                exif_data = piexif.load(image)
        except Error as e:
            exif_data = exif_data = {
                '0th': {
                    piexif.ImageIFD.XResolution: (width, 1),
                    piexif.ImageIFD.YResolution: (height, 1),
                }
            }
        # elif contenttype in ['image/tiff']:
        #     try:
        #         if getattr(image, 'read', None):
        #             exif_data = exifread.process_file(image)
        #             image.seek(0)
        #         else:
        #             exif_data = exifread.process_file(StringIO(image))
        #     except Error as e:
        #         exif_data = exif_data = {
        #             '0th': {
        #                 piexif.ImageIFD.XResolution: (width, 1),
        #                 piexif.ImageIFD.YResolution: (height, 1),
        #             }
        #         }
        return exif_data
    return None


def rotate_image(image_data, method=None, REQUEST=None):
    """Rotate Image if it has Exif Orientation Informations other than 1.

    Do not use PIL.Image.rotate function as this did not transpose the image,
    rotate keeps the image width and height and rotates the image around a
    central point. PIL.Image.transpose also changes Image Orientation.
    """
    if getattr(image_data, 'read', None):
        img = PIL.Image.open(image_data)
    else:
        img = PIL.Image.open(StringIO(image_data))

    if 'exif' in img.info:
        exif_data = piexif.load(img.info['exif'])

        if piexif.ImageIFD.Orientation in exif_data['0th']:
            orientation = exif_data['0th'][piexif.ImageIFD.Orientation]
    else:
        width, height = img.size
        exif_data = {
            '0th': {
                piexif.ImageIFD.XResolution: (width, 1),
                piexif.ImageIFD.YResolution: (height, 1),
            }
        }

    if method is not None:
        orientation = method

    log.debug('Rotate image with input orientation: %s', orientation)

    fmt = img.format
    if orientation == 1:  # not transform necessary
        # img = img
        pass
    elif orientation == 2:
        img = img.transpose(PIL.Image.FLIP_LEFT_RIGHT)
    elif orientation == 3:
        img = img.transpose(PIL.Image.ROTATE_180)
    elif orientation == 4:
        img = img.transpose(PIL.Image.ROTATE_180).transpose(PIL.Image.FLIP_LEFT_RIGHT)  # NOQA
    elif orientation == 5:
        img = img.transpose(PIL.Image.ROTATE_270).transpose(PIL.Image.FLIP_LEFT_RIGHT)  # NOQA
        exif_data['0th'][piexif.ImageIFD.XResolution], exif_data['0th'][piexif.ImageIFD.YResolution] = exif_data['0th'][piexif.ImageIFD.YResolution], exif_data['0th'][piexif.ImageIFD.XResolution]  # NOQA
    elif orientation == 6:
        img = img.transpose(PIL.Image.ROTATE_270)
        exif_data['0th'][piexif.ImageIFD.XResolution], exif_data['0th'][piexif.ImageIFD.YResolution] = exif_data['0th'][piexif.ImageIFD.YResolution], exif_data['0th'][piexif.ImageIFD.XResolution]  # NOQA
    elif orientation == 7:
        img = img.transpose(PIL.Image.ROTATE_90).transpose(PIL.Image.FLIP_LEFT_RIGHT)  # NOQA
        exif_data['0th'][piexif.ImageIFD.XResolution], exif_data['0th'][piexif.ImageIFD.YResolution] = exif_data['0th'][piexif.ImageIFD.YResolution], exif_data['0th'][piexif.ImageIFD.XResolution]  # NOQA
    elif orientation == 8:
        img = img.transpose(PIL.Image.ROTATE_90)
        exif_data['0th'][piexif.ImageIFD.XResolution], exif_data['0th'][piexif.ImageIFD.YResolution] = exif_data['0th'][piexif.ImageIFD.YResolution], exif_data['0th'][piexif.ImageIFD.XResolution]  # NOQA

    # set orientation to normal
    exif_data['0th'][piexif.ImageIFD.Orientation] = 1

    try:
        exif_bytes = piexif.dump(exif_data)
    except:
        del(exif_data['Exif'][piexif.ExifIFD.SceneType])
        # This Element piexif.ExifIFD.SceneType cause error on dump
        exif_bytes = piexif.dump(exif_data)
    output_image_data = StringIO()
    img.save(output_image_data, format=fmt, exif=exif_bytes)
    width, height = img.size
    return output_image_data.getvalue(), width, height, exif_data
