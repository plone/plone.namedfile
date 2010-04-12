import os.path
import mimetypes

from plone.namedfile.interfaces import HAVE_BLOBS

if HAVE_BLOBS:
    from plone.namedfile.interfaces import IBlobby

try:
    # use this to stream data if we can
    from ZPublisher.Iterators import filestream_iterator
except ImportError:
    filestream_iterator = None

def safe_basename(filename):
    """Get the basename of the given filename, regardless of which platform
    (Windows or Unix) it originated from.
    """
    return filename[max(filename.rfind('/'),
                        filename.rfind('\\'),
                        filename.rfind(':'),
                        )+1:]

def get_contenttype(file=None, filename=None, default='application/octet-stream'):
    """Get the MIME content type of the given file and/or filename.
    """
    
    file_type = getattr(file, 'contentType', None)
    if file_type is not None:
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
    
    response.setHeader("Content-Type", contenttype)
    response.setHeader("Content-Length", file.getSize())
    
    if filename is not None:
        response.setHeader("Content-Disposition", "attachment; filename=\"%s\"" % filename)

def stream_data(file):
    """Return the given file as a stream if possible.
    """

    if HAVE_BLOBS:
        if IBlobby.providedBy(file) and filestream_iterator is not None:
            # XXX: we may want to use this instead, which would raise an error
            # in case of uncomitted changes
            # filename = file._blob.committed()
            
            filename = file._blob._p_blob_uncommitted or file._blob.committed()
            return filestream_iterator(filename, 'rb')
    
    return file.data
