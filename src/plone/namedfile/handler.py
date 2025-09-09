from plone.namedfile import field
from plone.supermodel.exportimport import ObjectHandler


class FileFieldHandler(ObjectHandler):
    filteredAttributes = ObjectHandler.filteredAttributes.copy()
    filteredAttributes.update({"default": "rw", "missing_value": "rw", "schema": "rw"})


NamedFileHandler = FileFieldHandler(field.NamedFile)
NamedImageHandler = FileFieldHandler(field.NamedImage)

NamedBlobFileHandler = FileFieldHandler(field.NamedBlobFile)
NamedBlobImageHandler = FileFieldHandler(field.NamedBlobImage)
