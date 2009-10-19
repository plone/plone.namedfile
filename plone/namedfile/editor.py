from plone.namedfile.interfaces import HAVE_BLOBS
from plone.namedfile import field
from plone.schemaeditor.fields import FieldFactory

NamedFileFactory = FieldFactory(field.NamedFile, u'File Upload')
NamedImageFactory = FieldFactory(field.NamedImage, u'Image')

if HAVE_BLOBS:
    NamedBlobFileFactory = FieldFactory(field.NamedBlobFile, u'File Upload')
    NamedBlobImageFactory = FieldFactory(field.NamedBlobImage, u'Image')
