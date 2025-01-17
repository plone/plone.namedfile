from plone.namedfile import field
from plone.namedfile import file
from plone.namedfile.testing import PLONE_NAMEDFILE_INTEGRATION_TESTING
from plone.namedfile.tests import getFile

import unittest


class TestValidation(unittest.TestCase):

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def test_validation_NamedImage_default(self):
        # Testing the default accepted media types
        image_field = field.NamedImage(
            required=False,
        )

        # field is empty, passes
        image_field.validate(None)

        # field has an empty file, fails
        # NOTE: This fails not because the NamedFile is empty but because the
        #       fallback default mimetype is "application/octet-stream".
        #       Not sure, if we should change this behavior.
        #       See: plone.namedfile.utils.get_contenttype
        named_image = file.NamedImage()
        self.assertRaises(field.InvalidImageFile, image_field.validate, named_image)

        # field has an png image file, passes
        named_image = file.NamedImage(getFile("image.png"), filename="image.png")
        image_field.validate(named_image)

        # field has an gif image file, passes
        named_image = file.NamedImage(getFile("image.gif"), filename="image.gif")
        image_field.validate(named_image)

        # field has a non-image file, fails
        named_image = file.NamedImage(getFile("notimage.doc"), filename="notimage.doc")
        self.assertRaises(field.InvalidImageFile, image_field.validate, named_image)

    def test_validation_NamedImage_custom(self):
        # Testing the default accepted media types
        image_field = field.NamedImage(
            accept=("image/png", ".jpg"),
            required=False,
        )

        # field is empty, passes
        image_field.validate(None)

        # field has an empty file, fails
        # NOTE: This fails not because the NamedFile is empty but because the
        #       fallback default mimetype is "application/octet-stream".
        #       Not sure, if we should change this behavior.
        #       See: plone.namedfile.utils.get_contenttype
        named_image = file.NamedImage()
        self.assertRaises(field.InvalidImageFile, image_field.validate, named_image)

        # field has a png image file, passes
        named_image = file.NamedImage(getFile("image.png"), filename="image.png")
        image_field.validate(named_image)

        # field has a jpg image file, passes also
        named_image = file.NamedImage(getFile("image.jpg"), filename="image.jpg")
        image_field.validate(named_image)

        # field has a gif image file, fails because it's not in the accepted
        # media types
        named_image = file.NamedImage(getFile("image.gif"), filename="image.gif")
        self.assertRaises(field.InvalidImageFile, image_field.validate, named_image)

        # field has a non-image file, fails
        named_image = file.NamedImage(getFile("notimage.doc"), filename="notimage.doc")
        self.assertRaises(field.InvalidImageFile, image_field.validate, named_image)

    def test_validation_NamedFile_default(self):
        # Testing the default accepted media types
        file_field = field.NamedFile(
            required=False,
        )

        # field is empty, passes
        file_field.validate(None)

        # field has n pdf file file, passes
        named_file = file.NamedFile(getFile("file.pdf"), filename="file.pdf")
        file_field.validate(named_file)

        # field has a gif file, passes
        named_file = file.NamedFile(getFile("image.gif"), filename="image.gif")
        file_field.validate(named_file)

    def test_validation_NamedFile_custom(self):
        # Testing the default accepted media types
        file_field = field.NamedFile(
            accept=("application/pdf", ".jpg"),
            required=False,
        )

        # field is empty, passes
        file_field.validate(None)

        # field has a pdf file file, passes
        named_file = file.NamedFile(getFile("file.pdf"), filename="file.pdf")
        file_field.validate(named_file)

        # field has a jpg file file, passes also
        named_file = file.NamedFile(getFile("image.jpg"), filename="image.jpg")
        file_field.validate(named_file)

        # field has a gif file, fails because it's not in the accepted media
        # types
        named_file = file.NamedFile(getFile("image.gif"), filename="image.gif")
        self.assertRaises(field.InvalidFile, file_field.validate, named_file)
