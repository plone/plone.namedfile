# -*- coding: utf-8 -*-

from logging import getLogger
from plone.namedfile.interfaces import IBlobby
from plone.namedfile.utils.jpeg_utils import process_jpeg
from plone.namedfile.utils.png_utils import process_png
from plone.namedfile.utils.tiff_utils import process_tiff
from plone.registry.interfaces import IRegistry
from StringIO import StringIO
from zope.component import queryUtility
from zope.deprecation import deprecate

import mimetypes
import os.path
import piexif
import PIL.Image
import struct
import urllib


log = getLogger(__name__)

try:
    from Products.CMFPlone.interfaces.controlpanel import IImagingSchema
except ImportError:
    IImagingSchema = None
    log.info('IImagingSchema for high pixel density scales not available.')


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

    if IBlobby.providedBy(file):
        if file._blob._p_blob_uncommitted:
            return file.data
        if filestream_iterator is not None:
            return filestream_iterator(file._blob.committed(), 'rb')

    return file.data


def _ensure_data(image):
    data = None
    if getattr(image, 'read', None):
        data = image.read()
        image.seek(0)
    else:
        data = image
    return str(data)


def getImageInfo(data):
    data = _ensure_data(data)
    size = len(data)
    height = -1
    width = -1
    content_type = ''

    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # handle GIFs
        content_type = 'image/gif'
        w, h = struct.unpack('<HH', data[6:10])
        width = int(w)
        height = int(h)

    elif data[:8] == '\211PNG\r\n\032\n':
        # handle PNG
        content_type, width, height = process_png(data)

    elif data[:2] == '\377\330':
        # handle JPEGs
        content_type, width, height = process_jpeg(data)

    elif (size >= 30) and data.startswith('BM'):
        # handle BMPs
        kind = struct.unpack('<H', data[14:16])[0]
        if kind == 40:  # Windows 3.x bitmap
            content_type = 'image/x-ms-bmp'
            width, height = struct.unpack('<LL', data[18:26])

    elif (size >= 4) and data[:4] in ['MM\x00*', 'II*\x00']:
        # handle TIFFs
        content_type, width, height = process_tiff(data)

    else:
        # Use PIL / Pillow to determ Image Information
        try:
            img = PIL.Image.open(StringIO(data))
            width, height = img.size
            content_type = img.format
        except Exception:
            # TODO: determ wich error really happens
            # Should happen if data is to short --> first_bytes
            # happens also if data is an svg or another special format.
            log.warn(
                'PIL can not recognize the image. '
                'Image is probably broken or of a non-supported format.'
            )

    log.debug('Image Info (Type: %s, Width: %s, Height: %s)',
              content_type, width, height)
    return content_type, width, height


def get_exif(image):
    #
    exif_data = None
    image_data = _ensure_data(image)

    content_type, width, height = getImageInfo(image_data)
    if content_type in ['image/jpeg', 'image/tiff']:
        # Only this two Image Types could have Exif informations
        # see http://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf
        try:
            exif_data = piexif.load(image_data)
        except Exception as e:
            # TODO: determ wich error really happens
            # Should happen if data is to short --> first_bytes
            log.warn(e)
            exif_data = exif_data = {
                '0th': {
                    piexif.ImageIFD.XResolution: (width, 1),
                    piexif.ImageIFD.YResolution: (height, 1),
                }
            }
    return exif_data


def rotate_image(image_data, method=None, REQUEST=None):
    """Rotate Image if it has Exif Orientation Informations other than 1.

    Do not use PIL.Image.rotate function as this did not transpose the image,
    rotate keeps the image width and height and rotates the image around a
    central point. PIL.Image.transpose also changes Image Orientation.
    """
    orientation = 1  # if not set assume correct orrinetation --> 1
    data = _ensure_data(image_data)
    img = PIL.Image.open(StringIO(data))

    exif_data = None
    if 'exif' in img.info:
        try:
            exif_data = piexif.load(img.info['exif'])
        except ValueError:
            log.warn('Exif information currupt')
            pass
        if exif_data and piexif.ImageIFD.Orientation in exif_data['0th']:
            orientation = exif_data['0th'][piexif.ImageIFD.Orientation]
        if exif_data and \
                (not exif_data['0th'].get(piexif.ImageIFD.XResolution) or
                 not exif_data['0th'].get(piexif.ImageIFD.YResolution)):
            exif_data['0th'][piexif.ImageIFD.XResolution] = (img.width, 1)
            exif_data['0th'][piexif.ImageIFD.YResolution] = (img.height, 1)
    if exif_data is None:
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
        img = img.transpose(PIL.Image.ROTATE_180).transpose(
            PIL.Image.FLIP_LEFT_RIGHT)
    elif orientation == 5:
        img = img.transpose(PIL.Image.ROTATE_270).transpose(
            PIL.Image.FLIP_LEFT_RIGHT)
    elif orientation == 6:
        img = img.transpose(PIL.Image.ROTATE_270)
    elif orientation == 7:
        img = img.transpose(PIL.Image.ROTATE_90).transpose(
            PIL.Image.FLIP_LEFT_RIGHT)
    elif orientation == 8:
        img = img.transpose(PIL.Image.ROTATE_90)

    if orientation in [5, 6, 7, 8]:
        if exif_data['0th'][piexif.ImageIFD.XResolution] and \
                exif_data['0th'][piexif.ImageIFD.YResolution]:
            exif_data['0th'][piexif.ImageIFD.XResolution], \
                exif_data['0th'][piexif.ImageIFD.YResolution] = \
                exif_data['0th'][piexif.ImageIFD.YResolution], \
                exif_data['0th'][piexif.ImageIFD.XResolution]
        else:
            exif_data['0th'][piexif.ImageIFD.XResolution], \
                exif_data['0th'][piexif.ImageIFD.YResolution] = \
                (img.width, 1), (img.height, 1)

    # set orientation to normal
    exif_data['0th'][piexif.ImageIFD.Orientation] = 1

    try:
        exif_bytes = piexif.dump(exif_data)
    except Exception as e:
        log.warn(e)
        del(exif_data['Exif'][piexif.ExifIFD.SceneType])
        # This Element piexif.ExifIFD.SceneType cause error on dump
        exif_bytes = piexif.dump(exif_data)
    output_image_data = StringIO()
    img.save(output_image_data, format=fmt, exif=exif_bytes)
    width, height = img.size
    return output_image_data.getvalue(), width, height, exif_data

@deprecate('use getHighPixelDensityScales instead')
def getRetinaScales():
    return getHighPixelDensityScales()

def getHighPixelDensityScales():
    registry = queryUtility(IRegistry)
    if IImagingSchema and registry:
        settings = registry.forInterface(
            IImagingSchema, prefix='plone', check=False)
        if settings.highpixeldensity_scales == '2x':
            return [
                {'scale': 2, 'quality': settings.quality_2x},
            ]
        elif settings.highpixeldensity_scales == '3x':
            return [
                {'scale': 2, 'quality': settings.quality_2x},
                {'scale': 3, 'quality': settings.quality_3x},
            ]
    return []
