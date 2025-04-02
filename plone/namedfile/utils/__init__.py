from collections.abc import Iterable
from io import BytesIO
from io import FileIO
from logging import getLogger
from plone.base.interfaces import IImagingSchema
from plone.namedfile.interfaces import IBlobby
from plone.namedfile.utils.jpeg_utils import process_jpeg
from plone.namedfile.utils.png_utils import process_png
from plone.namedfile.utils.svg_utils import process_svg
from plone.registry.interfaces import IRegistry
from urllib.parse import quote
from zope.component import queryUtility
from zope.deprecation import deprecate
from zope.interface import implementer
from ZPublisher.Iterators import IStreamIterator

import mimetypes
import piexif
import PIL.Image
import re
import struct


# image-scaling
QUALITY_DEFAULT = 88
pattern = re.compile(r"^(.*)\s+(\d+)\s*:\s*(\d+)$")

log = getLogger(__name__)


try:
    # Zope 5.8.6+
    from OFS.Image import extract_media_type
except ImportError:

    def extract_media_type(content_type):
        """extract the proper media type from *content_type*.

        Ignore parameters and whitespace and normalize to lower case.
        See https://github.com/zopefoundation/Zope/pull/1167
        """
        if not content_type:
            return content_type
        # ignore parameters
        content_type = content_type.split(";", 1)[0]
        # ignore whitespace
        content_type = "".join(content_type.split())
        # normalize to lowercase
        return content_type.lower()


@implementer(IStreamIterator)
class filestream_range_iterator(Iterable):
    """
    A class that mimics FileIO and implements an iterator that returns a
    fixed-sized sequence of bytes. Beginning from `start` to `end`.

    BBB: due to a possible bug in Zope>4, <=4.1.3, couldn't be subclass of FileIO
         as Iterators.filestream_iterator
    """

    def __init__(
        self, name, mode="rb", bufsize=-1, streamsize=1 << 16, start=0, end=None
    ):
        self._io = FileIO(name, mode=mode)
        self.streamsize = streamsize
        self.start = start
        self.end = end
        self._io.seek(start, 0)

    def __iter__(self):
        if self._io.closed:
            raise ValueError("I/O operation on closed file.")
        return self

    def __next__(self):
        if self.end is None:
            bytes = self.streamsize
        else:
            bytes = max(min(self.end - self._io.tell(), self.streamsize), 0)
        data = self._io.read(bytes)
        if not data:
            raise StopIteration
        return data

    next = __next__

    def close(self):
        self._io.close()

    # BBB: is it necessary to implement __len__ ?
    # def __len__(self)

    def read(self, size=-1):
        return self._io.read(size)


def safe_basename(filename):
    """Get the basename of the given filename, regardless of which platform
    (Windows or Unix) it originated from.
    """
    fslice = (
        max(
            filename.rfind("/"),
            filename.rfind("\\"),
            filename.rfind(":"),
        )
        + 1
    )
    return filename[fslice:]


def get_contenttype(file=None, filename=None, default="application/octet-stream"):
    """Get the MIME content type of the given file and/or filename.

    Note: depending on your use case, you may want to call 'extract_media_type'
    on the result.
    """

    file_type = getattr(file, "contentType", None)
    if file_type:
        return file_type

    filename = getattr(file, "filename", filename)
    if filename:
        return mimetypes.guess_type(filename, strict=False)[0] or default

    return default


def set_headers(file, response, filename=None, canonical=None):
    """Set response headers for the given file. If filename is given, set
    the Content-Disposition to attachment.
    """

    contenttype = get_contenttype(file)

    response.setHeader("Content-Type", contenttype)
    response.setHeader("Content-Length", file.getSize())
    response.setHeader("Accept-Ranges", "bytes")

    if filename is not None:
        if not isinstance(filename, str):
            filename = str(filename, "utf-8", errors="ignore")
        filename = quote(filename.encode("utf8"))
        response.setHeader(
            "Content-Disposition", f"attachment; filename*=UTF-8''{filename}"
        )

    if canonical is not None:
        response.setHeader(
            "Link", f'<{quote(canonical, safe="/:&?=@")}>; rel="canonical"'
        )


def stream_data(file, start=0, end=None):
    """Return the given file as a stream if possible."""
    if IBlobby.providedBy(file):
        if file._blob._p_blob_uncommitted:
            return file.data[start:end]
        return filestream_range_iterator(
            file._blob.committed(), "rb", start=start, end=end
        )
    return file.data[start:end]


def _ensure_data(image):
    data = None
    if getattr(image, "read", None):
        data = image.read()
        image.seek(0)
    else:
        data = image
    return bytes(data)


def getImageInfo(data):
    data = _ensure_data(data)
    size = len(data)
    height = -1
    width = -1
    content_type = ""

    if (size >= 10) and data[:6] in (b"GIF87a", b"GIF89a"):
        # handle GIFs
        content_type = "image/gif"
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)

    elif data[:8] == b"\211PNG\r\n\032\n":
        # handle PNG
        content_type, width, height = process_png(data)

    elif data[:2] == b"\377\330":
        # handle JPEGs
        content_type, width, height = process_jpeg(data)

    elif (size >= 30) and data.startswith(b"BM"):
        # handle BMPs
        kind = struct.unpack("<H", data[14:16])[0]
        if kind == 40:  # Windows 3.x bitmap
            content_type = "image/x-ms-bmp"
            width, height = struct.unpack("<LL", data[18:26])

    elif size and b"http://www.w3.org/2000/svg" in data:
        # handle SVGs
        content_type, width, height = process_svg(data)

    else:
        # Use PIL / Pillow to determ Image Information
        try:
            img = PIL.Image.open(BytesIO(data))
            width, height = img.size
            content_type = PIL.Image.MIME[img.format]
        except Exception:
            # TODO: determ which error really happens
            # Should happen if data is to short --> first_bytes
            # happens also if data is an svg or another special format.
            log.warning(
                "PIL can not recognize the image. "
                "Image is probably broken or of a non-supported format."
            )

    log.debug(
        "Image Info (Type: %s, Width: %s, Height: %s)", content_type, width, height
    )
    return content_type, width, height


def get_exif(image, content_type=None, width=None, height=None):
    #
    exif_data = None

    if None in (content_type, width, height):
        # if we already got the image info don't read the while file into memory
        image = _ensure_data(image)
        content_type, width, height = getImageInfo(image)
    if content_type in ["image/jpeg", "image/tiff"]:
        # Only this two Image Types could have Exif information
        # see http://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf
        try:
            # if possible pass filename in instead to prevent reading all data into memory
            exif_data = piexif.load(
                image.name if getattr(image, "name") else _ensure_data(image)
            )
        except Exception as e:
            # TODO: determ which error really happens
            # Should happen if data is to short --> first_bytes
            log.warn(e)
            exif_data = exif_data = {
                "0th": {
                    piexif.ImageIFD.XResolution: (width, 1),
                    piexif.ImageIFD.YResolution: (height, 1),
                }
            }
    return exif_data


def rotate_image(image_data, method=None, REQUEST=None):
    """Rotate Image if it has Exif Orientation Information other than 1.

    Do not use PIL.Image.rotate function as this did not transpose the image,
    rotate keeps the image width and height and rotates the image around a
    central point. PIL.Image.transpose also changes Image Orientation.
    """
    orientation = 1  # if not set assume correct orrinetation --> 1
    data = _ensure_data(image_data)
    img = PIL.Image.open(BytesIO(data))

    exif_data = None
    if "exif" in img.info:
        try:
            exif_data = piexif.load(img.info["exif"])
        except ValueError:
            log.warn("Exif information corrupt")
            pass
        if exif_data and piexif.ImageIFD.Orientation in exif_data["0th"]:
            orientation = exif_data["0th"][piexif.ImageIFD.Orientation]
        if exif_data and (
            not exif_data["0th"].get(piexif.ImageIFD.XResolution)
            or not exif_data["0th"].get(piexif.ImageIFD.YResolution)
        ):
            exif_data["0th"][piexif.ImageIFD.XResolution] = (img.width, 1)
            exif_data["0th"][piexif.ImageIFD.YResolution] = (img.height, 1)
    if exif_data is None:
        width, height = img.size
        exif_data = {
            "0th": {
                piexif.ImageIFD.XResolution: (width, 1),
                piexif.ImageIFD.YResolution: (height, 1),
            }
        }

    if method is not None:
        orientation = method

    log.debug("Rotate image with input orientation: %s", orientation)

    fmt = img.format
    if orientation == 1:  # not transform necessary
        # img = img
        pass
    elif orientation == 2:
        img = img.transpose(PIL.Image.FLIP_LEFT_RIGHT)
    elif orientation == 3:
        img = img.transpose(PIL.Image.ROTATE_180)
    elif orientation == 4:
        img = img.transpose(PIL.Image.ROTATE_180).transpose(PIL.Image.FLIP_LEFT_RIGHT)
    elif orientation == 5:
        img = img.transpose(PIL.Image.ROTATE_270).transpose(PIL.Image.FLIP_LEFT_RIGHT)
    elif orientation == 6:
        img = img.transpose(PIL.Image.ROTATE_270)
    elif orientation == 7:
        img = img.transpose(PIL.Image.ROTATE_90).transpose(PIL.Image.FLIP_LEFT_RIGHT)
    elif orientation == 8:
        img = img.transpose(PIL.Image.ROTATE_90)

    if orientation in [5, 6, 7, 8]:
        if (
            exif_data["0th"][piexif.ImageIFD.XResolution]
            and exif_data["0th"][piexif.ImageIFD.YResolution]
        ):
            (
                exif_data["0th"][piexif.ImageIFD.XResolution],
                exif_data["0th"][piexif.ImageIFD.YResolution],
            ) = (
                exif_data["0th"][piexif.ImageIFD.YResolution],
                exif_data["0th"][piexif.ImageIFD.XResolution],
            )
        else:
            (
                exif_data["0th"][piexif.ImageIFD.XResolution],
                exif_data["0th"][piexif.ImageIFD.YResolution],
            ) = (img.width, 1), (img.height, 1)

    # set orientation to normal
    exif_data["0th"][piexif.ImageIFD.Orientation] = 1

    try:
        exif_bytes = piexif.dump(exif_data)
    except Exception as e:
        log.warn(e)
        del exif_data["Exif"][piexif.ExifIFD.SceneType]
        # This Element piexif.ExifIFD.SceneType cause error on dump
        exif_bytes = piexif.dump(exif_data)

    output_image_data = BytesIO()
    img.save(output_image_data, format=fmt, exif=exif_bytes)
    width, height = img.size
    return output_image_data.getvalue(), width, height, exif_data


@deprecate("use getHighPixelDensityScales instead")
def getRetinaScales():
    return getHighPixelDensityScales()


def getHighPixelDensityScales():
    registry = queryUtility(IRegistry)
    if not registry:
        return []
    settings = registry.forInterface(IImagingSchema, prefix="plone", check=False)
    if settings.highpixeldensity_scales == "2x":
        return [
            {"scale": 2, "quality": settings.quality_2x},
        ]
    if settings.highpixeldensity_scales == "3x":
        return [
            {"scale": 2, "quality": settings.quality_2x},
            {"scale": 3, "quality": settings.quality_3x},
        ]
    return []


def getAllowedSizes():
    registry = queryUtility(IRegistry)
    if not registry:
        return None
    settings = registry.forInterface(IImagingSchema, prefix="plone", check=False)
    if not settings.allowed_sizes:
        return None
    sizes = {}
    for line in settings.allowed_sizes:
        line = line.strip()
        if line:
            name, width, height = pattern.match(line).groups()
            name = name.strip().replace(" ", "_")
            sizes[name] = int(width), int(height)
    return sizes


def getQuality():
    registry = queryUtility(IRegistry)
    if registry:
        settings = registry.forInterface(IImagingSchema, prefix="plone", check=False)
        return settings.quality or QUALITY_DEFAULT
    return QUALITY_DEFAULT
