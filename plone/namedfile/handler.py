try:
    from plone.supermodel.exportimport import ObjectHandler
    HAVE_SUPERMODEL = True
except ImportError:
    HAVE_SUPERMODEL = False
    
if HAVE_SUPERMODEL:
    
    from plone.namedfile import field
    
    class FileFieldHandler(ObjectHandler):
        
        filteredAttributes = ObjectHandler.filteredAttributes.copy()
        filteredAttributes.update({'default': 'rw', 'missing_value': 'rw', 'schema': 'rw'})
    
    NamedFileHandler = FileFieldHandler(field.NamedFile)
    NamedImageHandler = FileFieldHandler(field.NamedImage)
    
    NamedBlobFileHandler = FileFieldHandler(field.NamedBlobFile)
    NamedBlobImageHandler = FileFieldHandler(field.NamedBlobImage)
