from zope.component import adapts
from zope.interface import implements

from Products.CMFCore.interfaces import IContentish

from plone.scale.storage import AnnotationStorage, IImageData
from plone.scale.storage import IImageScaleStorage

from plone.namedfile.interfaces import INamedBlobImage

class BlobImageData(object):
    implements(IImageData)
    adapts(INamedBlobImage)
    
    def __init__(self, field):
        self.field = field
    
    @property
    def data(self):
        return self.field.open()

# XXX add normal ImageData adapter

class NamedImageScaleStorage(AnnotationStorage):
    """:class:`plone.scale.storage IImageScaleStorage` implementation for
    Dexterity content
    """
    implements(IImageScaleStorage)
    adapts(IContentish)
    
    def __init__(self, context, request):
        AnnotationStorage.__init__(self, context)

    def _wrapImageData(self, fieldname, data, details):
        field_value = self._getField(fieldname)
        return field_value.__class__(data, details['mimetype'])

    def _url(self, id):
        return "%s/@@image-scale-download/%s" % (self.context.absolute_url(), id)
