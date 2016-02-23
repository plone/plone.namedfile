# -*- coding: utf-8 -*-
from AccessControl.ZopeGuards import guarded_getattr
from Acquisition import aq_base
from DateTime import DateTime
from logging import exception
from plone.namedfile.interfaces import IAvailableSizes
from plone.namedfile.interfaces import IStableImageScale
from plone.namedfile.utils import set_headers
from plone.namedfile.utils import stream_data
from plone.rfc822.interfaces import IPrimaryFieldInfo
from plone.scale.scale import scaleImage
from plone.scale.storage import AnnotationStorage
from Products.Five import BrowserView
from xml.sax.saxutils import quoteattr
from ZODB.POSException import ConflictError
from zope.app.file.file import FileChunk
from zope.component import queryUtility
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound
from zope.traversing.interfaces import ITraversable
from zope.traversing.interfaces import TraversalError

import pkg_resources


try:
    pkg_resources.get_distribution('plone.protect>=3.0')
except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
    IDisableCSRFProtection = None
else:
    # Soft dependency to make this package work without plone.protect
    from plone.protect.interfaces import IDisableCSRFProtection

_marker = object()


class ImageScale(BrowserView):
    """ view used for rendering image scales """

    # Grant full access to this view even if the object being viewed is
    # protected
    # (it's okay because we explicitly validate access to the image attribute
    # when we retrieve it)
    __roles__ = ('Anonymous',)
    __allow_access_to_unprotected_subobjects__ = 1

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

    def absolute_url(self):
        return self.url

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
            image = self.scale(name, scale)             # this is aq-wrapped
        elif '-' in name:
            # we got a uid...
            if '.' in name:
                name, ext = name.rsplit('.', 1)
            storage = AnnotationStorage(self.context)
            info = storage.get(name)
            if info is not None:
                scale_view = ImageScale(self.context, self.request, **info)
                alsoProvides(scale_view, IStableImageScale)
                return scale_view.__of__(self.context)
        else:
            # otherwise `name` must refer to a field...
            if '.' in name:
                name, ext = name.rsplit('.', 1)
            value = getattr(self.context, name)
            scale_view = ImageScale(
                self.context, self.request, data=value, fieldname=name)
            return scale_view.__of__(self.context)
        if image is not None:
            return image
        raise NotFound(self, name, self.request)

    def traverse(self, name, furtherPath):
        """ used for path traversal, i.e. in zope page templates """
        # validate access
        value = self.guarded_orig_image(name)
        if not furtherPath:
            image = ImageScale(
                self.context, self.request, data=value, fieldname=name)
        else:
            return ImmutableTraverser(self.scale(name, furtherPath[-1]))

        if image is not None:
            return image.tag()
        raise TraversalError(self, name)

    _sizes = {}

    def getAvailableSizes(self, fieldname=None):
        # fieldname is ignored by default
        getAvailableSizes = queryUtility(IAvailableSizes)
        if getAvailableSizes is None:
            return self._sizes
        sizes = getAvailableSizes()
        if sizes is None:
            return {}
        return sizes

    def _set_sizes(self, value):
        self._sizes = value

    available_sizes = property(getAvailableSizes, _set_sizes)

    def getImageSize(self, fieldname=None):
        if fieldname is not None:
            value = self.guarded_orig_image(fieldname)
            if value is None:
                return (0, 0)
            return value.getImageSize()
        value = IPrimaryFieldInfo(self.context).value
        return value.getImageSize()

    def guarded_orig_image(self, fieldname):
        return guarded_getattr(self.context, fieldname, None)

    def getQuality(self):
        """Get plone.app.imaging's quality setting"""
        # Avoid dependening on version where interface first
        # appeared.
        try:
            from plone.scale.interfaces import IScaledImageQuality
        except ImportError:
            return None
        getScaledImageQuality = queryUtility(IScaledImageQuality)
        if getScaledImageQuality is None:
            return None
        return getScaledImageQuality()

    def create(self,
               fieldname,
               direction='thumbnail',
               height=None,
               width=None,
               **parameters):
        """Factory for image scales, see `IImageScaleStorage.scale`.
        """
        orig_value = getattr(self.context, fieldname)
        if orig_value is None:
            return

        if height is None and width is None:
            _, format_ = orig_value.contentType.split('/', 1)
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
        if isinstance(orig_data, FileChunk):
            # Convert data to 8-bit string
            # (FileChunk does not provide read() access)
            orig_data = str(orig_data)

        # If quality wasn't in the parameters, try the site's default scaling
        # quality if it exists.
        if 'quality' not in parameters:
            quality = self.getQuality()
            if quality:
                parameters['quality'] = quality

        try:
            result = scaleImage(orig_data,
                                direction=direction,
                                height=height,
                                width=width,
                                **parameters)
        except (ConflictError, KeyboardInterrupt):
            raise
        except Exception:
            exception('could not scale "%r" of %r',
                      orig_value, self.context.absolute_url())
            return
        if result is not None:
            data, format_, dimensions = result
            mimetype = u'image/{0}'.format(format_.lower())
            value = orig_value.__class__(
                data, contentType=mimetype, filename=orig_value.filename)
            value.fieldname = fieldname
            return value, format_, dimensions

    def modified(self):
        """Provide a callable to return the modification time of content
        items, so stored image scales can be invalidated.
        """
        context = aq_base(self.context)
        date = DateTime(context._p_mtime)
        return date.millis()

    def scale(self,
              fieldname=None,
              scale=None,
              height=None,
              width=None,
              direction='thumbnail',
              **parameters):
        if fieldname is None:
            fieldname = IPrimaryFieldInfo(self.context).fieldname
        if scale is not None:
            available = self.getAvailableSizes(fieldname)
            if scale not in available:
                return None
            width, height = available[scale]

        if IDisableCSRFProtection and self.request is not None:
            alsoProvides(self.request, IDisableCSRFProtection)

        storage = AnnotationStorage(self.context, self.modified)
        info = storage.scale(factory=self.create,
                             fieldname=fieldname,
                             height=height,
                             width=width,
                             direction=direction,
                             **parameters)

        if info is not None:
            info['fieldname'] = fieldname
            scale_view = ImageScale(self.context, self.request, **info)
            return scale_view.__of__(self.context)

    def tag(self,
            fieldname=None,
            scale=None,
            height=None,
            width=None,
            direction='thumbnail',
            **kwargs):
        scale = self.scale(fieldname, scale, height, width, direction)
        return scale.tag(**kwargs) if scale else None
