from plone.namedfile import interfaces
from plone.namedfile.interfaces import HAVE_BLOBS
from plone.namedfile import field
from plone.schemaeditor.fields import FieldFactory

class INamedFileField(interfaces.INamedFileField):

    default = field.NamedFile(
        title=interfaces.INamedFileField['default'].title,
        description=interfaces.INamedFileField['default'].description,
        required=False)

    missing_value = field.NamedFile(
        title=interfaces.INamedFileField['missing_value'].title,
        description=interfaces.INamedFileField[
            'missing_value'].description,
        required=False)

class INamedImageField(interfaces.INamedImageField):

    default = field.NamedImage(
        title=interfaces.INamedImageField['default'].title,
        description=interfaces.INamedImageField[
            'default'].description,
        required=False)

    missing_value = field.NamedImage(
        title=interfaces.INamedImageField['missing_value'].title,
        description=interfaces.INamedImageField[
            'missing_value'].description,
        required=False)

NamedFileFactory = FieldFactory(field.NamedFile, u'File Upload')
NamedImageFactory = FieldFactory(field.NamedImage, u'Image')

if HAVE_BLOBS:

    class INamedBlobFileField(interfaces.INamedBlobFileField):
    
        default = field.NamedBlobFile(
            title=interfaces.INamedBlobFileField['default'].title,
            description=interfaces.INamedBlobFileField[
                'default'].description,
            required=False)
    
        missing_value = field.NamedBlobFile(
            title=interfaces.INamedBlobFileField[
                'missing_value'].title,
            description=interfaces.INamedBlobFileField[
                'missing_value'].description,
            required=False)
    
    class INamedBlobImageField(interfaces.INamedBlobImageField):
    
        default = field.NamedBlobImage(
            title=interfaces.INamedBlobImageField['default'].title,
            description=interfaces.INamedBlobImageField[
                'default'].description,
            required=False)
    
        missing_value = field.NamedBlobImage(
            title=interfaces.INamedBlobImageField[
                'missing_value'].title,
            description=interfaces.INamedBlobImageField[
                'missing_value'].description,
            required=False)

    NamedBlobFileFactory = FieldFactory(field.NamedBlobFile, u'File Upload')
    NamedBlobImageFactory = FieldFactory(field.NamedBlobImage, u'Image')
