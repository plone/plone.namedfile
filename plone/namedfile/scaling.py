from cgi import escape
from logging import exception
from Acquisition import aq_base
from AccessControl.ZopeGuards import guarded_getattr
from ZODB.POSException import ConflictError
from zope.component import queryUtility
from zope.interface import implements
from zope.traversing.interfaces import ITraversable, TraversalError
from zope.publisher.interfaces import IPublishTraverse, NotFound
from plone.scale.storage import AnnotationStorage
from plone.scale.scale import scaleImage
from Products.Five import BrowserView

from plone.namedfile.interfaces import IAvailableSizes
from plone.namedfile.utils import set_headers, stream_data

class ImageScale(BrowserView):
    """ view used for rendering image scales """
    
    __allow_access_to_unprotected_subobjects__ = 1
    
    def __init__(self, context, request, **info):
        self.context = context
        self.request = request
        self.__dict__.update(**info)

        url = self.context.absolute_url()
        extension = self.data.contentType.split('/')[-1].lower()
        if 'uid' in info:
            self.__name__ = '%s.%s' % (info['uid'], extension)
            self.url = '%s/@@images/%s' % (url, self.__name__)
        else:
            self.__name__ = info['fieldname']
            self.url = '%s/@@images/%s' % (url, info['fieldname'])

    def absolute_url(self):
        return self.url

    def tag(self, height=None, width=None, alt=None,
            css_class=None, title=None, **kwargs):
        """Create a tag including scale
        """
        if height is None:
            height = getattr(self, 'height', self.data._height)
        if width is None:
            width = getattr(self, 'width', self.data._width)

        if alt is None:
            alt = self.context.Title()
        if title is None:
            title = self.context.Title()

        values = {'src' : self.url,
                  'alt' : escape(alt, quote=True),
                  'title' : escape(title, quote=True),
                  'height' : height,
                  'width' : width,
                 }

        result = '<img src="%(src)s" alt="%(alt)s" title="%(title)s" '\
                 'height="%(height)s" width="%(width)s"' % values

        if css_class is not None:
            result = '%s class="%s"' % (result, css_class)

        for key, value in kwargs.items():
            if value:
                result = '%s %s="%s"' % (result, key, value)

        return '%s />' % result

    def index_html(self):
        """ download the image """
        # validate access
        fieldname = getattr(self.data, 'fieldname', getattr(self, 'fieldname', None))
        guarded_getattr(self.context, fieldname)
        set_headers(self.data, self.request.response, filename=self.data.filename)
        return stream_data(self.data)

    def __call__(self):
        # avoid the need to prefix with nocall: in TAL
        return self

class ImageScaling(BrowserView):
    """ view used for generating (and storing) image scales """
    implements(ITraversable, IPublishTraverse)

    def publishTraverse(self, request, name):
        """ used for traversal via publisher, i.e. when using as a url """
        stack = request.get('TraversalRequestNameStack')
        image = None
        if stack:
            # field and scale name were given...
            scale = stack.pop()
            image = self.scale(name, scale)             # this is aq-wrapped
        elif '.' in name:
            # we got a uid...
            uid, ext = name.rsplit('.', 1)
            storage = AnnotationStorage(self.context)
            info = storage.get(uid)
            if info is not None:
                scale_view = ImageScale(self.context, self.request, **info)
                return scale_view.__of__(self.context)
        else:
            # otherwise `name` must refer to a field...
            value = getattr(self.context, name)
            scale_view = ImageScale(self.context, self.request, data=value, fieldname=name)
            return scale_view.__of__(self.context)
        if image is not None:
            return image
        raise NotFound(self, name, self.request)

    def traverse(self, name, furtherPath):
        """ used for path traversal, i.e. in zope page templates """
        # validate access
        value = self.guarded_orig_image(name)
        if not furtherPath:
            image = ImageScale(self.context, self.request, data=value, fieldname=name)
        else:
            image = self.scale(name, furtherPath.pop())
        if image is not None:
            return image.tag()
        raise TraversalError(self, name)

    _sizes = {}
    @apply
    def available_sizes():
        def get(self):
            getAvailableSizes = queryUtility(IAvailableSizes)
            if getAvailableSizes is None:
                return self._sizes
            sizes = getAvailableSizes()
            if sizes is None:
                return {}
            return sizes
        def set(self, value):
            self._sizes = value
        return property(get, set)
    
    def guarded_orig_image(self, fieldname):
        return guarded_getattr(self.context, fieldname)

    def create(self, fieldname, direction='thumbnail', **parameters):
        """ factory for image scales, see `IImageScaleStorage.scale` """
        orig_value = getattr(self.context, fieldname)
        if hasattr(aq_base(orig_value), 'open'):
            orig_data = orig_value.open()
        else:
            orig_data = getattr(aq_base(orig_value), 'data', orig_value)
        if not orig_data:
            return
        try:
            result = scaleImage(orig_data, direction=direction, **parameters)
        except (ConflictError, KeyboardInterrupt):
            raise
        except Exception:
            exception('could not scale "%r" of %r',
                orig_value, self.context.absolute_url())
            return
        if result is not None:
            data, format, dimensions = result
            mimetype = 'image/%s' % format.lower()
            value = orig_value.__class__(data, contentType=mimetype, filename=orig_value.filename)
            value.fieldname = fieldname
            return value, format, dimensions

    def modified(self):
        """ provide a callable to return the modification time of content
            items, so stored image scales can be invalidated """
        return self.context.modified().millis()

    def scale(self, fieldname=None, scale=None, **parameters):
        if scale is not None:
            available = self.available_sizes
            if not scale in available:
                return None
            width, height = available[scale]
            parameters.update(width=width, height=height)
        storage = AnnotationStorage(self.context, self.modified)
        info = storage.scale(factory=self.create,
            fieldname=fieldname, **parameters)
        if info is not None:
            scale_view = ImageScale(self.context, self.request, **info)
            return scale_view.__of__(self.context)
