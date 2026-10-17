from plone.namedfile.scaling import _image_tag_from_values
from plone.namedfile.scaling import _marker
from plone.namedfile.scaling import ImageScale
from plone.namedfile.scaling import ImageScaling
from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.interfaces import ICatalogBrain
from zExceptions import BadRequest
from zope.cachedescriptors.property import Lazy as lazy_property
from zope.component import getMultiAdapter
from zope.publisher.interfaces import NotFound
from zope.traversing.interfaces import TraversalError

import logging

logger = logging.getLogger(__name__)


def _title(context):
    """Return a normalized title for a brain, wrapper, or content object."""
    title = getattr(context, "Title", "")
    if callable(title):
        title = title()
    return title or ""


def _scale_url_from_download(metadata_origin, download):
    if download.startswith(("http://", "https://", "/")):
        return download
    return f"{metadata_origin.getURL().rstrip('/')}/{download.lstrip('/')}"


def _extension(content_type, download):
    if content_type == "image/svg+xml":
        return "svg"
    if content_type and "/" in content_type:
        return content_type.rsplit("/", 1)[-1].lower()
    path = download.split("?", 1)[0].split("#", 1)[0]
    filename = path.rsplit("/", 1)[-1]
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return "img"


class BrainImageScale(ImageScale):
    """An ``ImageScale``-compatible object backed by catalog metadata.

    ``.data`` is None and no storage ``uid`` is exposed; only metadata-backed
    URLs and dimensions are available.
    """

    def __init__(
        self,
        context,
        request,
        *,
        fieldname,
        scale=None,
        download=None,
        width=None,
        height=None,
        content_type=None,
        filename=None,
    ):
        if not download:
            raise ValueError("BrainImageScale requires a download URL")
        self.context = context
        self.request = request
        self.fieldname = fieldname
        self.scale = scale
        self.download = download
        self.width = width
        self.height = height
        self.contentType = content_type
        self.mimetype = content_type
        self.filename = filename
        self.data = None
        self.srcset = []
        extension = _extension(content_type, download)
        name = f"{fieldname}-{scale}" if scale else fieldname
        self.__name__ = f"{name}.{extension}"
        self.url = _scale_url_from_download(context, download)

    @property
    def title(self):
        return _title(self.context)

    def srcset_attribute(self):
        return ""

    def validate_access(self):
        return None

    def tag(
        self,
        height=_marker,
        width=_marker,
        alt=_marker,
        css_class=None,
        title=_marker,
        **kwargs,
    ):
        if height is _marker:
            height = self.height
        if width is _marker:
            width = self.width
        if alt is _marker:
            alt = self.title
        if title is _marker:
            title = self.title

        values = [
            ("src", self.url),
            ("alt", alt),
            ("title", title),
            ("height", height),
            ("width", width),
            ("class", css_class),
        ]
        srcset_attr = self.srcset_attribute()
        if srcset_attr:
            values.append(("srcset", srcset_attr))
        values.extend(kwargs.items())
        return _image_tag_from_values(*values)

    def index_html(self):
        raise NotFound(self, self.__name__, self.request)

    def HEAD(self, REQUEST, RESPONSE=None):
        raise NotFound(self, self.__name__, self.request)

    HEAD.__roles__ = ("Anonymous",)

    def set_headers(self, response=None):
        raise NotFound(self, self.__name__, self.request)


class BrainImageScaling(ImageScaling):
    """The ``@@images`` view for catalog brains and contentlisting wrappers.

    Metadata-first methods and the object fallback are implemented by the
    later implementation tickets; this class owns registration, context
    resolution, field resolution, and traversal refusal.
    """

    @lazy_property
    def _supports_image_scales_metadata(self):
        catalog = getToolByName(self.context, "portal_catalog")
        return "image_scales" in catalog._catalog.schema

    def _metadata_origin(self):
        """Return the brain behind the context, or None for a real object."""
        context = self.context
        get_data_origin = getattr(context, "getDataOrigin", None)
        origin = get_data_origin() if callable(get_data_origin) else context
        return origin if ICatalogBrain.providedBy(origin) else None

    def _object_view(self, origin):
        """Return the object-backed ``@@images`` view for a metadata origin."""
        obj = origin.getObject() if ICatalogBrain.providedBy(origin) else origin
        return getMultiAdapter((obj, self.request), name="images")

    def _resolve_metadata(self, fieldname=None):
        """Resolve a field name and its first metadata entry."""
        origin = self._metadata_origin()
        metadata = getattr(origin, "image_scales", None) if origin is not None else None
        if not metadata:
            logger.debug("@@images found no image scales metadata")
            return None, None
        if fieldname is not None:
            entries = metadata.get(fieldname)
            if not entries:
                return None, None
            if len(entries) > 1:
                logger.debug(
                    "@@images uses the first of %s entries for field %r",
                    len(entries),
                    fieldname,
                )
            return fieldname, entries[0]
        names = list(metadata.keys())
        if len(names) != 1:
            logger.debug(
                "@@images cannot choose a field on this brain: %s",
                names,
            )
            return None, None
        entries = metadata[names[0]]
        if not entries:
            return None, None
        if len(entries) > 1:
            logger.debug(
                "@@images uses the first of %s entries for field %r",
                len(entries),
                names[0],
            )
        return names[0], entries[0]

    def publishTraverse(self, request, name):
        raise NotFound(self, name, request)

    def traverse(self, name, furtherPath):
        raise TraversalError(self, name)

    def browserDefault(self, request):
        raise BadRequest("@@images is not available on catalog brains")
