from DateTime import DateTime

from plone.namedfile.tests.base import NamedFileTestCase, getFile

from zope.annotation import IAttributeAnnotatable
from zope.interface import implements
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.namedfile.field import NamedImage as NamedImageField
from plone.namedfile.file import NamedImage
from plone.namedfile.scaling import ImageScaling

class IHasImage(IImageScaleTraversable):
    image = NamedImageField()

class DummyContent(object):
    implements(IAttributeAnnotatable, IHasImage)
    image = None
    modified = DateTime
    def absolute_url(self):
        return 'http://dummy'

class ImageScalingTests(NamedFileTestCase):

    def assertImage(self, image, format, size):
        self.assertEqual(image.contentType, format)
        self.assertEqual(image.getImageSize(), size)

    def afterSetUp(self):
        data = getFile('image.gif').read()
        self.item = DummyContent()
        self.item.image = NamedImage(data, 'image/gif', 'image.gif')
        self.scaling = ImageScaling(self.item, None)
        self.scaling.available_sizes = {'foo': (60,60)}

    def testCreateScale(self):
        foo = self.scaling.scale('image', width=100, height=80)
        self.failUnless(foo.uid)
        self.assertEqual(foo.mimetype, 'image/jpeg')
        self.assertEqual(foo.width, 80)
        self.assertEqual(foo.height, 80)
        self.assertImage(foo.data, 'JPEG', (80, 80))

    def testCreateScaleWithoutData(self):
        item = DummyContent()
        scaling = ImageScaling(item, None)
        foo = scaling.scale('image', width=100, height=80)
        self.assertEqual(foo, None)

    def testGetScaleByName(self):
        foo = self.scaling.scale('image', scale='foo')
        self.failUnless(foo.uid)
        self.assertEqual(foo.mimetype, 'image/jpeg')
        self.assertEqual(foo.width, 60)
        self.assertEqual(foo.height, 60)
        self.assertImage(foo.data, 'JPEG', (60, 60))

    def testGetUnknownScale(self):
        foo = self.scaling.scale('image', scale='foo?')
        self.assertEqual(foo, None)

    def testScaleInvalidation(self):
        # first get the scale of the original image
        foo1 = self.scaling.scale('image', scale='foo')
        # now upload a new one and make sure the scale has changed
        data = getFile('image.jpg').read()
        self.item.image = NamedImage(data, 'image/jpeg', 'image.jpg')
        foo2 = self.scaling.scale('image', scale='foo')
        self.failIf(foo1.data == foo2.data, 'scale not updated?')

    def testCustomSizeChange(self):
        # set custom image sizes & view a scale
        self.scaling.available_sizes = {'foo': (23,23)}
        foo = self.scaling.scale('image', scale='foo')
        self.assertEqual(foo.width, 23)
        self.assertEqual(foo.height, 23)
        # now let's update the scale dimensions, after which the scale
        # shouldn't be the same...
        self.scaling.available_sizes = {'foo': (42,42)}
        foo = self.scaling.scale('image', scale='foo')
        self.assertEqual(foo.width, 42)
        self.assertEqual(foo.height, 42)

def test_suite():
    from unittest import defaultTestLoader 
    return defaultTestLoader.loadTestsFromName(__name__)
