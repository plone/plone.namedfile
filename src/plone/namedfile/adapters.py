from plone.dexterity.interfaces import IDexterityContent
from plone.namedfile.interfaces import INamedImageField
from plone.registry.interfaces import IRegistry
from zope.component import adapter
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.interface import implementer
from zope.interface import Interface
from zope.interface.interfaces import ComponentLookupError


try:
    from plone.base.interfaces import IImageScalesFieldAdapter
    from plone.base.interfaces import IImagingSchema
except ImportError:
    # BBB Plone 5
    IImageScalesFieldAdapter = Interface
    IImagingSchema = None


def _split_scale_info(allowed_size):
    name, dims = allowed_size.split(" ")
    width, height = list(map(int, dims.split(":")))
    return name, width, height


def _get_scale_infos():
    """Returns list of (name, width, height) of the available image scales."""
    if IImagingSchema is None:
        return []
    registry = getUtility(IRegistry)
    imaging_settings = registry.forInterface(IImagingSchema, prefix="plone")
    allowed_sizes = imaging_settings.allowed_sizes
    return [_split_scale_info(size) for size in allowed_sizes]


@implementer(IImageScalesFieldAdapter)
@adapter(INamedImageField, IDexterityContent, Interface)
class ImageFieldScales:
    def __init__(self, field, context, request):
        self.context = context
        self.request = request
        self.field = field

    def __call__(self):
        image = self.field.get(self.context)
        if not image:
            return

        # Get the @@images view once and store it, so all methods can use it.
        try:
            self.images_view = getMultiAdapter(
                (self.context, self.request), name="images"
            )
        except ComponentLookupError:
            # Seen in plone.app.caching.tests.test_profile_with_caching_proxy.
            # If we cannot find the images view, there is nothing for us to do.
            return
        width, height = image.getImageSize()
        url = self.get_original_image_url(self.field.__name__, width, height)
        scales = self.get_scales(self.field, width, height)

        # Return a list with one dictionary.  Why a list?
        # Some people feel a need in custom code to support a different adapter for
        # RelationList fields.  Such a field may point to three images.
        # In that case the adapter could return information for all three images,
        # so a list of three dictionaries.  The default case should use the same
        # structure.
        return [
            {
                "filename": image.filename,
                "content-type": image.contentType,
                "size": image.getSize(),
                "download": self._scale_view_from_url(url),
                "width": width,
                "height": height,
                "scales": scales,
            }
        ]

    def get_scales(self, field, width, height):
        """Get a dictionary of available scales for a particular image field,
        with the actual dimensions (aspect ratio of the original image).
        """
        scales = {}

        for name, actual_width, actual_height in _get_scale_infos():
            if actual_width > width:
                # The width of the scale is larger than the original width.
                # Scaling would simply return the original (or perhaps a copy
                # with the same size).  We do not need this scale.
                # If we *do* want this, we should call the scale method with
                # mode="cover", so it scales up.
                continue

            # Get the scale info without actually generating the scale,
            # nor any old-style HiDPI scales.
            scale = self.images_view.scale(
                field.__name__,
                width=actual_width,
                height=actual_height,
                pre=True,
                include_srcset=False,
            )
            if scale is None:
                # If we cannot get a scale, it is probably a corrupt image.
                continue

            url = scale.url
            actual_width = scale.width
            actual_height = scale.height

            scales[name] = {
                "download": self._scale_view_from_url(url),
                "width": actual_width,
                "height": actual_height,
            }

        return scales

    def get_original_image_url(self, fieldname, width, height):
        scale = self.images_view.scale(
            fieldname,
            width=width,
            height=height,
            pre=True,
            include_srcset=False,
        )
        # Corrupt images may not have a scale.
        return scale.url if scale else None

    def _scale_view_from_url(self, url):
        # The "download" information for scales is the path to
        # "@@images/foo-scale" only.
        # The full URL to the scale is rendered by the scaling adapter at
        # runtime to make sure they are correct in virtual hostings.
        return url.replace(self.context.absolute_url(), "").lstrip("/")
