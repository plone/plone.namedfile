# -*- coding: utf-8 -*-
from AccessControl.ZopeGuards import guarded_getattr
from Acquisition import aq_base
from DateTime import DateTime
from plone.memoize import ram
from plone.namedfile.file import FILECHUNK_CLASSES
from plone.namedfile.interfaces import IAvailableSizes
from plone.namedfile.interfaces import IStableImageScale
from plone.namedfile.utils import getHighPixelDensityScales
from plone.namedfile.utils import set_headers
from plone.namedfile.utils import stream_data
from plone.protect.interfaces import IDisableCSRFProtection
from plone.rfc822.interfaces import IPrimaryFieldInfo
from plone.scale.interfaces import IImageScaleFactory
from plone.scale.interfaces import IScaledImageQuality
from plone.scale.scale import scaleImage
from plone.scale.storage import AnnotationStorage
from Products.Five import BrowserView
from xml.sax.saxutils import quoteattr
from zExceptions import Unauthorized
from ZODB.POSException import ConflictError
from zope.component import queryUtility
from zope.deprecation import deprecate
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound
from zope.traversing.interfaces import ITraversable
from zope.traversing.interfaces import TraversalError

import logging


logger = logging.getLogger(__name__)
_marker = object()


class ImageScale(BrowserView):
    """ view used for rendering image scales """

    # Grant full access to this view even if the object being viewed is
    # protected
    # (it's okay because we explicitly validate access to the image attribute
    # when we retrieve it)
    __roles__ = ('Anonymous',)
    __allow_access_to_unprotected_subobjects__ = 1
    data = None

    def __init__(self, context, request, **info):
        self.context = context
        self.request = request
        self.__dict__.update(**info)
        if self.data is None:
            self.data = getattr(self.context, self.fieldname)

        url = self.context.absolute_url()
        extension = self.data.contentType.split('/')[-1].lower()
        if 'uid' in info:
            name = info['uid']
        else:
            name = info['fieldname']
        self.__name__ = u'{0}.{1}'.format(name, extension)
        self.url = u'{0}/@@images/{1}'.format(url, self.__name__)
        self.srcset = info.get('srcset', [])

    def absolute_url(self):
        return self.url

    def srcset_attribute(self):
        _srcset_attr = []
        extension = self.data.contentType.split('/')[-1].lower()
        for scale in self.srcset:
            _srcset_attr.append(u'{0}/@@images/{1}.{2} {3}x'.format(
                self.context.absolute_url(),
                scale['uid'],
                extension,
                scale['scale']))
        srcset_attr = ', '.join(_srcset_attr)
        return srcset_attr

    def tag(self, height=_marker, width=_marker, alt=_marker,
            css_class=None, title=_marker, **kwargs):
        """Create a tag including scale
        """
        if height is _marker:
            height = getattr(self, 'height', self.data._height)
        if width is _marker:
            width = getattr(self, 'width', self.data._width)

        if alt is _marker:
            alt = self.context.Title()
        if title is _marker:
            title = self.context.Title()

        values = [
            ('src', self.url),
            ('alt', alt),
            ('title', title),
            ('height', height),
            ('width', width),
            ('class', css_class),
        ]

        srcset_attr = self.srcset_attribute()
        if srcset_attr:
            values.append(('srcset', srcset_attr))

        values.extend(kwargs.items())

        parts = ['<img']
        for k, v in values:
            if v is None:
                continue
            if isinstance(v, int):
                v = str(v)
            elif isinstance(v, str):
                v = unicode(v, 'utf8')
            parts.append(u'{0}={1}'.format(k, quoteattr(v)))
        parts.append('/>')

        return u' '.join(parts)

    def validate_access(self):
        fieldname = getattr(self.data, 'fieldname',
                            getattr(self, 'fieldname', None))
        guarded_getattr(self.context, fieldname)

    def index_html(self):
        """ download the image """
        self.validate_access()
        set_headers(self.data, self.request.response)
        return stream_data(self.data)

    def manage_DAVget(self):
        """Get scale via webdav."""
        return self.manage_FTPget()

    def manage_FTPget(self):
        """Get scale via ftp."""
        return self.index_html()

    def __call__(self):
        # avoid the need to prefix with nocall: in TAL
        return self

    def HEAD(self, REQUEST, RESPONSE=None):
        """ Obtain metainformation about the image implied by the request
            without transfer of the image itself
        """
        self.validate_access()
        set_headers(self.data, REQUEST.response)
        return ''

    HEAD.__roles__ = ('Anonymous',)


@implementer(ITraversable)
class ImmutableTraverser(object):

    def __init__(self, scale):
        self.scale = scale

    def traverse(self, name, furtherPath):
        if furtherPath:
            raise TraversalError('Do not know how to handle further path')
        else:
            if self.scale:
                return self.scale.tag()
            else:
                raise TraversalError(name)


@implementer(IImageScaleFactory)
class DefaultImageScalingFactory(object):

    def __init__(self, context):
        self.context = context

    def get_quality(self):
        """Get plone.app.imaging's quality setting"""
        getScaledImageQuality = queryUtility(IScaledImageQuality)
        if getScaledImageQuality is None:
            return None
        return getScaledImageQuality()

    def create_scale(self, data, direction, height, width, **parameters):
        return scaleImage(
            data,
            direction=direction,
            height=height,
            width=width,
            **parameters
        )

    def __call__(
            self,
            fieldname=None,
            direction='thumbnail',
            height=None,
            width=None,
            scale=None,
            **parameters
    ):

        """Factory for image scales`.
        """
        orig_value = getattr(self.context, fieldname, None)
        if orig_value is None:
            return

        if height is None and width is None:
            dummy, format_ = orig_value.contentType.split('/', 1)
            return None, format_, (orig_value._width, orig_value._height)
        orig_data = None
        try:
            orig_data = orig_value.open()
        except AttributeError:
            orig_data = getattr(aq_base(orig_value), 'data', orig_value)
        if not orig_data:
            return

        # Handle cases where large image data is stored in FileChunks instead
        # of plain string
        if isinstance(orig_data, tuple(FILECHUNK_CLASSES)):
            # Convert data to 8-bit string
            # (FileChunk does not provide read() access)
            orig_data = str(orig_data)

        # If quality wasn't in the parameters, try the site's default scaling
        # quality if it exists.
        if 'quality' not in parameters:
            quality = self.get_quality()
            if quality:
                parameters['quality'] = quality

        try:
            result = self.create_scale(
                orig_data,
                direction=direction,
                height=height,
                width=width,
                **parameters
            )
        except (ConflictError, KeyboardInterrupt):
            raise
        except IOError:
            if getattr(orig_value, 'contentType', '') == 'image/svg+xml':
                result = orig_data.read(), 'SVG', (width, height)
            else:
                logger.exception(
                    'Could not scale "{0!r}" of {1!r}'.format(
                        orig_value,
                        self.context.absolute_url,
                    ),
                )
                return
        except Exception:
            logger.exception(
                'Could not scale "{0!r}" of {1!r}'.format(
                    orig_value,
                    self.context.absolute_url,
                ),
            )
            return
        if result is None:
            return

        data, format_, dimensions = result
        mimetype = 'image/{0}'.format(format_.lower())
        value = orig_value.__class__(
            data,
            contentType=mimetype,
            filename=orig_value.filename,
        )
        value.fieldname = fieldname
        return value, format_, dimensions


@implementer(ITraversable, IPublishTraverse)
class ImageScaling(BrowserView):
    """ view used for generating (and storing) image scales """
    # Ignore some stacks to help with accessing via webdav, otherwise you get a
    # 404 NotFound error.
    _ignored_stacks = ('manage_DAVget', 'manage_FTPget')

    def publishTraverse(self, request, name):
        """ used for traversal via publisher, i.e. when using as a url """
        stack = request.get('TraversalRequestNameStack')
        image = None
        if stack and stack[-1] not in self._ignored_stacks:
            # field and scale name were given...
            scale = stack.pop()
            image = self.scale(name, scale)  # this is an aq-wrapped scale_view
            if image:
                return image
        elif '-' in name:
            # we got a uid...
            if '.' in name:
                name, ext = name.rsplit('.', 1)
            storage = AnnotationStorage(self.context)
            info = storage.get(name)
            if info is None:
                raise NotFound(self, name, self.request)
            scale_view = ImageScale(self.context, self.request, **info)
            alsoProvides(scale_view, IStableImageScale)
            return scale_view
        else:
            # otherwise `name` must refer to a field...
            if '.' in name:
                name, ext = name.rsplit('.', 1)
            value = getattr(self.context, name)
            scale_view = ImageScale(
                self.context,
                self.request,
                data=value,
                fieldname=name,
            )
            return scale_view
        raise NotFound(self, name, self.request)

    def traverse(self, name, furtherPath):
        """ used for path traversal, i.e. in zope page templates """
        # validate access
        value = self.guarded_orig_image(name)
        if not furtherPath:
            image = ImageScale(
                self.context,
                self.request,
                data=value,
                fieldname=name,
            )
        else:
            return ImmutableTraverser(self.scale(name, furtherPath[-1]))

        if image is not None:
            return image.tag()
        raise TraversalError(self, name)

    _sizes = {}

    @deprecate('use property available_sizes instead')
    def getAvailableSizes(self, fieldname=None):
        if fieldname:
            logger.warn(
                'fieldname was passed to deprecated getAvailableSizes, but '
                'will be ignored.',
            )
        return self.available_sizes

    @property
    def available_sizes(self):
        # fieldname is ignored by default
        sizes_util = queryUtility(IAvailableSizes)
        if sizes_util is None:
            return self._sizes
        sizes = sizes_util()
        if sizes is None:
            return {}
        return sizes

    @available_sizes.setter
    def available_sizes(self, value):
        self._sizes = value

    def getImageSize(self, fieldname=None):
        if fieldname is not None:
            try:
                value = self.guarded_orig_image(fieldname)
            except Unauthorized:
                # This is a corner case that can be seen in some tests,
                # at least plone.app.caching and plone.formwidget.namedfile.
                # When it is *really* unauthorized to get this image,
                # it will go wrong somewhere else.
                value = None
            if value is None:
                return (0, 0)
            return value.getImageSize()
        value = IPrimaryFieldInfo(self.context).value
        return value.getImageSize()

    def guarded_orig_image(self, fieldname):
        return guarded_getattr(self.context, fieldname, None)

    @deprecate('use getHighPixelDensityScales instead')
    def getRetinaScales(self):
        return getHighPixelDensityScales()

    def getHighPixelDensityScales(self):
        return getHighPixelDensityScales()

    def modified(self):
        """Provide a callable to return the modification time of content
        items, so stored image scales can be invalidated.
        """
        context = aq_base(self.context)
        date = DateTime(context._p_mtime)
        return date.millis()

    def scale(
        self,
        fieldname=None,
        scale=None,
        height=None,
        width=None,
        direction='thumbnail',
        **parameters
    ):
        if fieldname is None:
            primary_field = IPrimaryFieldInfo(self.context, None)
            if primary_field is None:
                return  # 404
            fieldname = primary_field.fieldname
        if scale is not None:
            if width is not None or height is not None:
                logger.warn(
                    'A scale name and width/heigth are given. Those are'
                    'mutually exclusive: solved by ignoring width/heigth and '
                    'taking name',
                )
            available = self.available_sizes
            if scale not in available:
                return None  # 404
            width, height = available[scale]
        if IDisableCSRFProtection and self.request is not None:
            alsoProvides(self.request, IDisableCSRFProtection)
        storage = AnnotationStorage(self.context, self.modified)
        info = storage.scale(
            fieldname=fieldname,
            height=height,
            width=width,
            direction=direction,
            scale=scale,
            **parameters
        )
        if info is None:
            return  # 404

        info['srcset'] = self.calculate_srcset(
            fieldname=fieldname,
            height=height,
            width=width,
            direction=direction,
            scale=scale,
            storage=storage,
            **parameters
        )
        info['fieldname'] = fieldname
        scale_view = ImageScale(self.context, self.request, **info)
        return scale_view

    def calculate_srcset(
        self,
        fieldname=None,
        scale=None,
        height=None,
        width=None,
        direction='thumbnail',
        storage=None,
        **parameters
    ):
        srcset = []
        if storage is None:
            return srcset
        (orig_width, orig_height) = self.getImageSize(fieldname)
        for hdScale in self.getHighPixelDensityScales():
            # Don't create retina scales larger than the source image.
            if (
                (
                    height and
                    orig_height and
                    orig_height < height * hdScale['scale']
                ) or (
                    width and
                    orig_width and
                    orig_width < width * hdScale['scale']
                )
            ):
                continue
            parameters['quality'] = hdScale['quality']
            scale_src = storage.scale(
                fieldname=fieldname,
                height=height * hdScale['scale'] if height else height,
                width=width * hdScale['scale'] if width else width,
                direction=direction,
                **parameters
            )
            scale_src['scale'] = hdScale['scale']
            if scale_src is not None:
                srcset.append(scale_src)
        return srcset

    def tag(
        self,
        fieldname=None,
        scale=None,
        height=None,
        width=None,
        direction='thumbnail',
        **kwargs
    ):
        scale = self.scale(fieldname, scale, height, width, direction)
        return scale.tag(**kwargs) if scale else None


class NavigationRootScaling(ImageScaling):
    def _scale_cachekey(method, self, brain, fieldname, **kwargs):
        return (
            self.context.absolute_url(),
            brain.UID,
            brain.modified,
            fieldname,
            kwargs,
        )

    @ram.cache(_scale_cachekey)
    def tag(self,
            brain,
            fieldname,
            **kwargs):
        obj = brain.getObject()
        images = obj.restrictedTraverse('@@images')
        tag = images.tag(fieldname, **kwargs)
        return tag
