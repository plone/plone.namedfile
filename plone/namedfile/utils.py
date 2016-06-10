# -*- coding: utf-8 -*-
from plone.namedfile.interfaces import IBlobby

import mimetypes
import os.path
import urllib


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
