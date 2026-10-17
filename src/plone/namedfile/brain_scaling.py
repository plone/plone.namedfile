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
