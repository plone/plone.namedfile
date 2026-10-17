from DateTime import DateTime
from Missing import Value as MissingValue
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

    Scale and accessor methods answer from catalog metadata first and delegate
    to the real object when metadata cannot answer. Traversal is refused.
    """

    @lazy_property
    def _supports_image_scales_metadata(self):
        origin = self._metadata_origin()
        catalog = getToolByName(origin or self.context, "portal_catalog")
        return "image_scales" in catalog._catalog.schema

    def _context_origin(self):
        get_data_origin = getattr(self.context, "getDataOrigin", None)
        return get_data_origin() if callable(get_data_origin) else self.context

    def _metadata_origin(self):
        """Return the brain behind the context, or None for a real object."""
        origin = self._context_origin()
        return origin if ICatalogBrain.providedBy(origin) else None

    def _resolved_origin(self):
        """Return the brain or the real object behind the current context."""
        origin = self._metadata_origin()
        return origin if origin is not None else self._context_origin()

    def _object_view(self, origin):
        """Return the object-backed ``@@images`` view for a metadata origin."""
        obj = origin.getObject() if ICatalogBrain.providedBy(origin) else origin
        if obj is None:
            logger.debug("@@images fallback object is missing for %r", origin)
            return None
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

    @staticmethod
    def _is_valid_entry(entry):
        """Return True for a dict with a string download and int dimensions."""
        if not isinstance(entry, dict):
            return False
        download = entry.get("download")
        width = entry.get("width")
        height = entry.get("height")
        return (
            isinstance(download, str)
            and bool(download)
            and isinstance(width, int)
            and not isinstance(width, bool)
            and isinstance(height, int)
            and not isinstance(height, bool)
        )

    @staticmethod
    def _match_dimensions(entry, width, height):
        scales = entry.get("scales", {})
        if not isinstance(scales, dict):
            return None, None

        def matches(data):
            if not isinstance(data, dict):
                return False
            if width is not None and data.get("width") != width:
                return False
            if height is not None and data.get("height") != height:
                return False
            return True

        if matches(entry):
            return None, entry
        for name, data in scales.items():
            if matches(data):
                return name, data
        return None, None

    def _build_scale(self, origin, fieldname, scale_name, data, entry):
        return BrainImageScale(
            origin,
            self.request,
            fieldname=fieldname,
            scale=scale_name,
            download=data["download"],
            width=data.get("width"),
            height=data.get("height"),
            content_type=entry.get("content-type"),
            filename=entry.get("filename"),
        )

    def _fallback_scale(
        self,
        fieldname,
        scale,
        height,
        width,
        mode,
        pre,
        include_srcset,
        reason,
        **parameters,
    ):
        logger.debug(
            "@@images falling back to object for %r/%r: %s",
            fieldname,
            scale,
            reason,
        )
        view = self._object_view(self._resolved_origin())
        if view is None:
            return None
        return view.scale(
            fieldname=fieldname,
            scale=scale,
            height=height,
            width=width,
            mode=mode,
            pre=pre,
            include_srcset=include_srcset,
            **parameters,
        )

    def scale(
        self,
        fieldname=None,
        scale=None,
        height=None,
        width=None,
        mode="scale",
        pre=False,
        include_srcset=None,
        **parameters,
    ):
        origin = self._metadata_origin()
        if origin is None:
            return self._fallback_scale(
                fieldname,
                scale,
                height,
                width,
                mode,
                pre,
                include_srcset,
                reason="not a metadata origin",
                **parameters,
            )
        if not self._supports_image_scales_metadata:
            return self._fallback_scale(
                fieldname,
                scale,
                height,
                width,
                mode,
                pre,
                include_srcset,
                reason="catalog has no image_scales column",
                **parameters,
            )

        fieldname, entry = self._resolve_metadata(fieldname)
        if entry is None:
            return None
        if not isinstance(entry, dict):
            return self._fallback_scale(
                fieldname,
                scale,
                height,
                width,
                mode,
                pre,
                include_srcset,
                reason="malformed image_scales entry",
                **parameters,
            )

        if scale is not None and scale not in self.available_sizes:
            return None
        if parameters or mode != "scale":
            return self._fallback_scale(
                fieldname,
                scale,
                height,
                width,
                mode,
                pre,
                include_srcset,
                reason="unsupported parameters or mode",
                **parameters,
            )

        if scale is not None:
            if width is not None or height is not None:
                logger.warning(
                    "A scale name and width/height are given. Those are "
                    "mutually exclusive: solved by ignoring width/height and "
                    "taking name",
                )
            scales = entry.get("scales", {})
            if not isinstance(scales, dict):
                return self._fallback_scale(
                    fieldname,
                    scale,
                    height,
                    width,
                    mode,
                    pre,
                    include_srcset,
                    reason="malformed scales metadata",
                    **parameters,
                )
            data = scales.get(scale)
            if not data or not self._is_valid_entry(data):
                return self._fallback_scale(
                    fieldname,
                    scale,
                    height,
                    width,
                    mode,
                    pre,
                    include_srcset,
                    reason="missing or malformed metadata scale",
                    **parameters,
                )
            return self._build_scale(origin, fieldname, scale, data, entry)

        if width is None and height is None:
            if not self._is_valid_entry(entry):
                return self._fallback_scale(
                    fieldname,
                    scale,
                    height,
                    width,
                    mode,
                    pre,
                    include_srcset,
                    reason="malformed original metadata",
                    **parameters,
                )
            return self._build_scale(origin, fieldname, None, entry, entry)

        matched_name, matched_data = self._match_dimensions(entry, width, height)
        if matched_data is None or not self._is_valid_entry(matched_data):
            return self._fallback_scale(
                fieldname,
                scale,
                height,
                width,
                mode,
                pre,
                include_srcset,
                reason="no matching metadata scale",
                **parameters,
            )
        return self._build_scale(origin, fieldname, matched_name, matched_data, entry)

    def tag(
        self,
        fieldname=None,
        scale=None,
        height=None,
        width=None,
        mode="scale",
        include_srcset=None,
        **kwargs,
    ):
        scale_object = self.scale(
            fieldname,
            scale,
            height,
            width,
            mode,
            pre=True,
            include_srcset=include_srcset,
        )
        return scale_object.tag(**kwargs) if scale_object else None

    def _fallback_srcset(
        self,
        fieldname,
        scale_in_src,
        sizes,
        alt,
        css_class,
        title,
        reason,
        **kwargs,
    ):
        logger.debug(
            "@@images srcset falling back for %r: %s",
            fieldname,
            reason,
        )
        view = self._object_view(self._resolved_origin())
        if view is None:
            return None
        return view.srcset(
            fieldname=fieldname,
            scale_in_src=scale_in_src,
            sizes=sizes,
            alt=alt,
            css_class=css_class,
            title=title,
            **kwargs,
        )

    def srcset(
        self,
        fieldname=None,
        scale_in_src="huge",
        sizes="",
        alt=_marker,
        css_class=None,
        title=_marker,
        **kwargs,
    ):
        origin = self._metadata_origin()
        if origin is None:
            return self._fallback_srcset(
                fieldname,
                scale_in_src,
                sizes,
                alt,
                css_class,
                title,
                reason="not a metadata origin",
                **kwargs,
            )
        if not self._supports_image_scales_metadata:
            return self._fallback_srcset(
                fieldname,
                scale_in_src,
                sizes,
                alt,
                css_class,
                title,
                reason="catalog has no image_scales column",
                **kwargs,
            )

        fieldname, entry = self._resolve_metadata(fieldname)
        if entry is None:
            return None
        if not isinstance(entry, dict) or not self._is_valid_entry(entry):
            return self._fallback_srcset(
                fieldname,
                scale_in_src,
                sizes,
                alt,
                css_class,
                title,
                reason="malformed original metadata",
                **kwargs,
            )

        original_width = entry["width"]
        original_height = entry["height"]
        if not original_width or not original_height:
            return self._fallback_srcset(
                fieldname,
                scale_in_src,
                sizes,
                alt,
                css_class,
                title,
                reason="zero original dimensions",
                **kwargs,
            )

        scales = entry.get("scales", {})
        if not isinstance(scales, dict):
            return self._fallback_srcset(
                fieldname,
                scale_in_src,
                sizes,
                alt,
                css_class,
                title,
                reason="malformed scales metadata",
                **kwargs,
            )

        available_widths = {width for width, height in self.available_sizes.values()}
        srcset_urls = []
        if original_width not in available_widths:
            url = _scale_url_from_download(origin, entry["download"])
            srcset_urls.append(f"{url} {original_width}w")

        for name, (configured_width, configured_height) in self.available_sizes.items():
            if configured_width > original_width:
                continue
            data = scales.get(name)
            if data is None:
                logger.debug("@@images srcset skips missing scale %r", name)
                continue
            if not self._is_valid_entry(data):
                return self._fallback_srcset(
                    fieldname,
                    scale_in_src,
                    sizes,
                    alt,
                    css_class,
                    title,
                    reason=f"malformed scale metadata for {name!r}",
                    **kwargs,
                )
            url = _scale_url_from_download(origin, data["download"])
            srcset_urls.append(f"{url} {data['width']}w")

        selected_name = scale_in_src
        if selected_name not in self.available_sizes:
            selected_name = None
            for name, (
                configured_width,
                configured_height,
            ) in self.available_sizes.items():
                if configured_width <= original_width:
                    selected_name = name
                    break
            if selected_name is None:
                return None

        selected_data = scales.get(selected_name)
        if not selected_data or not self._is_valid_entry(selected_data):
            return self._fallback_srcset(
                fieldname,
                scale_in_src,
                sizes,
                alt,
                css_class,
                title,
                reason="selected scale missing from metadata",
                **kwargs,
            )

        attributes = {}
        default_title = _title(self.context)
        if title is _marker:
            attributes["title"] = default_title
        elif title:
            attributes["title"] = title
        if alt is _marker:
            attributes["alt"] = default_title
        else:
            attributes["alt"] = alt
        if css_class is not None:
            attributes["class"] = css_class
        attributes.update(**kwargs)
        attributes["sizes"] = sizes
        attributes["srcset"] = ", ".join(srcset_urls)
        attributes["src"] = _scale_url_from_download(
            origin,
            selected_data["download"],
        )
        if "width" not in attributes:
            attributes["width"] = selected_data["width"]
        if "height" not in attributes:
            attributes["height"] = selected_data["height"]

        return _image_tag_from_values(*attributes.items())

    def getImageSize(self, fieldname=None):
        origin = self._metadata_origin()
        if origin is None:
            logger.debug("@@images getImageSize falling back: not a metadata origin")
            view = self._object_view(self._resolved_origin())
            return view.getImageSize(fieldname) if view else (0, 0)
        if not self._supports_image_scales_metadata:
            logger.debug(
                "@@images getImageSize falling back: catalog has no "
                "image_scales column"
            )
            view = self._object_view(self._resolved_origin())
            return view.getImageSize(fieldname) if view else (0, 0)
        fieldname, entry = self._resolve_metadata(fieldname)
        if entry is None:
            return (0, 0)
        width = entry.get("width") if isinstance(entry, dict) else None
        height = entry.get("height") if isinstance(entry, dict) else None
        if (
            not isinstance(width, int)
            or isinstance(width, bool)
            or not isinstance(height, int)
            or isinstance(height, bool)
        ):
            logger.debug("@@images getImageSize falling back: malformed dimensions")
            view = self._object_view(self._resolved_origin())
            return view.getImageSize(fieldname) if view else (0, 0)
        return (width, height)

    def modified(self, fieldname=None):
        origin = self._metadata_origin()
        if origin is None:
            logger.debug("@@images modified falling back: not a metadata origin")
            view = self._object_view(self._resolved_origin())
            return view.modified(fieldname) if view else 0
        if not self._supports_image_scales_metadata:
            logger.debug(
                "@@images modified falling back: catalog has no " "image_scales column"
            )
            view = self._object_view(self._resolved_origin())
            return view.modified(fieldname) if view else 0
        value = getattr(origin, "modified", None)
        if value is None or value is MissingValue:
            return 0
        try:
            return DateTime(value).millis()
        except (TypeError, ValueError, SyntaxError):
            return 0

    def publishTraverse(self, request, name):
        raise NotFound(self, name, request)

    def traverse(self, name, furtherPath):
        raise TraversalError(self, name)

    def browserDefault(self, request):
        raise BadRequest("@@images is not available on catalog brains")
