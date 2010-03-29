from logging import exception
from Acquisition import aq_base
from ZODB.POSException import ConflictError
#from zope.interface import implements
#from zope.traversing.interfaces import ITraversable, TraversalError
#from zope.publisher.interfaces import IPublishTraverse, NotFound
# XXX needs to move to plone.scale?
#from plone.app.imaging.interfaces import IImageScaleFactory
from plone.scale.storage import AnnotationStorage
from plone.scale.scale import scaleImage
from Products.Five import BrowserView

from plone.namedfile.utils import set_headers, stream_data

# class ImageScaleFactory(object):
#     """ adapter for image fields that allows generating scaled images """
#     implements(IImageScaleFactory)
#     adapts(INamedImageField)
# 
#     def __init__(self, field):
#         self.field = field
# 
#     def create(self, context, **parameters):
#         value = self.field.get(context)
#         data = getattr(aq_base(value), 'data', value)
#         if data:
#             return scaleImage(data, **parameters)

class ImageScale(BrowserView):
    """ view used for rendering image scales """
    
    def __init__(self, context, request, **info):
        self.context = context
        self.request = request
        self.__dict__.update(**info)

        url = self.context.absolute_url()
        extension = info['mimetype'].split('/')[-1]
        self.url = '%s/@@images/%s.%s' % (url, info['uid'], extension)

    def absolute_url(self):
        return self.url

    def tag(self, **kw):
        # XXX
        raise NotImplemented

    def __call__(self):
        """ download the image """
        set_headers(self.data, self.request.response, filename=self.data.filename)
        return stream_data(self.data)
        
        # XXX return self?

class ImageScaling(BrowserView):
    """ view used for generating (and storing) image scales """
#    implements(IImageScaling, ITraversable, IPublishTraverse)

    # def publishTraverse(self, request, name):
    #     """ used for traversal via publisher, i.e. when using as a url """
    #     stack = request.get('TraversalRequestNameStack')
    #     if stack:
    #         # field and scale name were given...
    #         scale = stack.pop()
    #         image = self.scale(name, scale)             # this is aq-wrapped
    #     elif '.' in name:
    #         # we got a uid...
    #         uid, ext = name.rsplit('.', 1)
    #         storage = AnnotationStorage(self.context)
    #         info = storage.get(uid)
    #         if info is not None:
    #             image = self.make(info).__of__(self.context)
    #     else:
    #         # otherwise `name` must refer to a field...
    #         field = self.field(name)
    #         image = field.get(self.context)             # this is aq-wrapped
    #     if image is not None:
    #         return image
    #     raise NotFound(self, name, self.request)

    # def traverse(self, name, furtherPath):
    #     """ used for path traversal, i.e. in zope page templates """
    #     if not furtherPath:
    #         field = self.context.getField(name)
    #         return field.get(self.context).tag()
    #     image = self.scale(name, furtherPath.pop())
    #     if image is not None:
    #         return image.tag()
    #     raise TraversalError(self, name)

    # XXX use plone.app.imaging.utils.getAllowedSizes if present
    available_sizes = {}

    def create(self, fieldname, direction='keep', **parameters):
        """ factory for image scales, see `IImageScaleStorage.scale` """
        orig_value = getattr(self.context, fieldname)
        # XXX adapter to make work for blob and non-blob
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
            value = orig_value.__class__(data, contentType=format, filename=orig_value.filename)
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
