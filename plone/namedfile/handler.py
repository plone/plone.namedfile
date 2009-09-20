try:
    from plone.supermodel.exportimport import ObjectHandler
    HAVE_SUPERMODEL = True
except ImportError:
    HAVE_SUPERMODEL = False
    
if HAVE_SUPERMODEL:

    from zope.interface import implements
    from zope.component import adapts
    
    from plone.namedfile import field
    from plone.namedfile.interfaces import HAVE_BLOBS
    
    class FileFieldHandler(ObjectHandler):
        
        filteredAttributes = ObjectHandler.filteredAttributes.copy()
        filteredAttributes.update({'default': 'rw', 'missing_value': 'rw', 'schema': 'rw'})
    
    NamedFileHandler = FileFieldHandler(field.NamedFile)
    NamedImageHandler = FileFieldHandler(field.NamedImage)
    
    if HAVE_BLOBS:
        NamedBlobFileHandler = FileFieldHandler(field.NamedBlobFile)
        NamedBlobImageHandler = FileFieldHandler(field.NamedBlobImage)
