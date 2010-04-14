import re
from DateTime import DateTime
from OFS.SimpleItem import SimpleItem
from zExceptions import Unauthorized

from plone.namedfile.tests.base import NamedFileTestCase, getFile
from plone.namedfile.tests.base import NamedFileFunctionalTestCase

from zope.annotation import IAttributeAnnotatable
from zope.component import getSiteManager
from zope.interface import implements
from plone.namedfile.interfaces import IImageScaleTraversable, IAvailableSizes
from plone.namedfile.field import NamedImage as NamedImageField
from plone.namedfile.file import NamedImage
from plone.namedfile.scaling import ImageScaling

class IHasImage(IImageScaleTraversable):
    image = NamedImageField()

class DummyContent(SimpleItem):
    implements(IAttributeAnnotatable, IHasImage)
    image = None
    modified = DateTime
    id = __name__ = 'item'
    title = 'foo'
    def Title(self):
        return self.title

class ImageScalingTests(NamedFileTestCase):

    def afterSetUp(self):
        data = getFile('image.gif').read()
        item = DummyContent()
        item.image = NamedImage(data, 'image/gif', 'image.gif')
        self.app._setOb('item', item)
        self.item = self.app.item
        self.scaling = ImageScaling(self.app.item, None)

    def testCreateScale(self):
        foo = self.scaling.scale('image', width=100, height=80)
        self.failUnless(foo.uid)
        self.assertEqual(foo.mimetype, 'image/jpeg')
        self.assertEqual(foo.width, 80)
        self.assertEqual(foo.height, 80)
        self.assertImage(foo.data.data, 'JPEG', (80, 80))

    def testCreateScaleWithoutData(self):
        item = DummyContent()
        scaling = ImageScaling(item, None)
        foo = scaling.scale('image', width=100, height=80)
        self.assertEqual(foo, None)

    def testGetScaleByName(self):
        self.scaling.available_sizes = {'foo': (60,60)}
        foo = self.scaling.scale('image', scale='foo')
        self.failUnless(foo.uid)
        self.assertEqual(foo.mimetype, 'image/jpeg')
        self.assertEqual(foo.width, 60)
        self.assertEqual(foo.height, 60)
        self.assertImage(foo.data.data, 'JPEG', (60, 60))
        expected_url = re.compile(r'http://nohost/item/@@images/[-a-z0-9]{36}\.jpeg')
        self.failUnless(expected_url.match(foo.absolute_url()))
        self.assertEqual(foo.url, foo.absolute_url())
        
        tag = foo.tag()
        base = self.item.absolute_url()
        expected = r'<img src="%s/@@images/([-0-9a-f]{36}).(jpeg|gif|png)" ' \
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" />' % base
        groups = re.match(expected, tag).groups()
        self.failUnless(groups, tag)

    def testGetUnknownScale(self):
        foo = self.scaling.scale('image', scale='foo?')
        self.assertEqual(foo, None)

    def testScaleInvalidation(self):
        # first get the scale of the original image
        self.scaling.available_sizes = {'foo': (23,23)}
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

    def testAvailableSizes(self):
        # by default, no named scales are configured
        self.assertEqual(self.scaling.available_sizes, {})
        # a callable can be used to look up the available sizes
        def custom_available_sizes():
            return {'bar': (10,10)}
        sm = getSiteManager()
        sm.registerUtility(component=custom_available_sizes, provided=IAvailableSizes)
        self.assertEqual(self.scaling.available_sizes, {'bar': (10,10)})
        sm.unregisterUtility(provided=IAvailableSizes)
        # for testing purposes, the sizes may also be set directly on
        # the scaling adapter
        self.scaling.available_sizes = {'qux': (12, 12)}
        self.assertEqual(self.scaling.available_sizes, {'qux': (12, 12)})
    
    def testGuardedAccess(self):
        # make sure it's not possible to access scales of forbidden images
        self.item.__allow_access_to_unprotected_subobjects__ = 0
        self.assertRaises(Unauthorized, self.scaling.guarded_orig_image, 'image')
        self.item.__allow_access_to_unprotected_subobjects__ = 1

class ImageTraverseTests(NamedFileTestCase):

    def afterSetUp(self):
        data = getFile('image.gif').read()
        item = DummyContent()
        item.image = NamedImage(data, 'image/gif', 'image.gif')
        self.app._setOb('item', item)
        self.item = self.app.item
        self._orig_sizes = ImageScaling.available_sizes

    def beforeTearDown(self):
        ImageScaling.available_sizes = self._orig_sizes
    
    def traverse(self, path=''):
        view = self.item.unrestrictedTraverse('@@images')
        stack = path.split('/')
        name = stack.pop(0)
        tag = view.traverse(name, stack)
        base = self.item.absolute_url()
        expected = r'<img src="%s/@@images/([-0-9a-f]{36}).(jpeg|gif|png)" ' \
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" />' % base
        groups = re.match(expected, tag).groups()
        self.failUnless(groups, tag)
        uid, ext, height, width = groups
        return uid, ext, int(width), int(height)

    def testImageThumb(self):
        ImageScaling.available_sizes = {'thumb': (128,128)}
        uid, ext, width, height = self.traverse('image/thumb')
        self.assertEqual((width, height), ImageScaling.available_sizes['thumb'])
        self.assertEqual(ext, 'jpeg')

    def testCustomSizes(self):
        # set custom image sizes
        ImageScaling.available_sizes = {'foo': (23,23)}
        # make sure traversing works with the new sizes
        uid, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 23)
        self.assertEqual(height, 23)

    def testScaleInvalidation(self):
        # first view the thumbnail of the original image
        ImageScaling.available_sizes = {'thumb': (128,128)}
        uid1, ext, width1, height1 = self.traverse('image/thumb')
        # now upload a new one and make sure the thumbnail has changed
        data = getFile('image.jpg').read()
        self.item.image = NamedImage(data, 'image/jpeg', 'image.jpg')
        uid2, ext, width2, height2 = self.traverse('image/thumb')
        self.assertNotEqual(uid1, uid2, 'thumb not updated?')
        # the height also differs as the original image had a size of 200, 200
        # whereas the updated one has 500, 200...
        self.assertEqual(width1, width2)
        self.assertNotEqual(height1, height2)

    def testCustomSizeChange(self):
        # set custom image sizes & view a scale
        ImageScaling.available_sizes = {'foo': (23,23)}
        uid1, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 23)
        self.assertEqual(height, 23)
        # now let's update the scale dimensions, after which the scale
        # should also have been updated...
        ImageScaling.available_sizes = {'foo': (42,42)}
        uid2, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 42)
        self.assertEqual(height, 42)
        self.assertNotEqual(uid1, uid2, 'scale not updated?')

    def testGuardedAccess(self):
        # make sure it's not possible to access scales of forbidden images
        self.item.__allow_access_to_unprotected_subobjects__ = 0
        ImageScaling.available_sizes = {'foo': (42,42)}
        self.assertRaises(Unauthorized, self.traverse, 'image/foo')
        self.item.__allow_access_to_unprotected_subobjects__ = 1

class ImagePublisherTests(NamedFileFunctionalTestCase):

    def afterSetUp(self):
        data = getFile('image.gif').read()
        item = DummyContent()
        item.image = NamedImage(data, 'image/gif', 'image.gif')
        self.app._setOb('item', item)
        self.item = self.app.item
        self.view = self.item.unrestrictedTraverse('@@images')
        self._orig_sizes = ImageScaling.available_sizes
    
    def beforeTearDown(self):
        ImageScaling.available_sizes = self._orig_sizes

    def testPublishScaleViaUID(self):
        scale = self.view.scale('image', width=64, height=64)
        # make sure the referenced image scale is available
        url = scale.url.replace('http://nohost', '')
        response = self.publish(url, basic=self.getCredentials())
        self.assertEqual(response.getStatus(), 200)
        self.assertEqual(response.getHeader('Content-Type'), 'image/jpeg')
        self.assertImage(response.getBody(), 'JPEG', (64, 64))

    def testPublishThumbViaUID(self):
        ImageScaling.available_sizes = {'thumb': (128,128)}
        scale = self.view.scale('image', 'thumb')
        # make sure the referenced image scale is available
        url = scale.url.replace('http://nohost', '')
        response = self.publish(url, basic=self.getCredentials())
        self.assertEqual(response.getStatus(), 200)
        self.assertEqual(response.getHeader('Content-Type'), 'image/jpeg')
        self.assertImage(response.getBody(), 'JPEG', (128, 128))

    def testPublishCustomSizeViaUID(self):
        # set custom image sizes
        ImageScaling.available_sizes = {'foo': (23,23)}
        scale = self.view.scale('image', 'foo')
        # make sure the referenced image scale is available
        url = scale.url.replace('http://nohost', '')
        response = self.publish(url, basic=self.getCredentials())
        self.assertEqual(response.getStatus(), 200)
        self.assertEqual(response.getHeader('Content-Type'), 'image/jpeg')
        self.assertImage(response.getBody(), 'JPEG', (23, 23))

    def testPublishThumbViaName(self):
        ImageScaling.available_sizes = {'thumb': (128,128)}
        # make sure traversing works as is and with scaling
        credentials = self.getCredentials()
        # first the field without a scale name
        response = self.publish('/item/@@images/image', basic=credentials)
        self.assertEqual(response.getStatus(), 200)
        self.assertEqual(response.getBody(), getFile('image.gif').read())
        self.assertEqual(response.getHeader('Content-Type'), 'image/gif')
        # and last a scaled version
        response = self.publish('/item/@@images/image/thumb', basic=credentials)
        self.assertEqual(response.getStatus(), 200)
        self.assertEqual(response.getHeader('Content-Type'), 'image/jpeg')
        self.assertImage(response.getBody(), 'JPEG', (128, 128))

    def testPublishCustomSizeViaName(self):
        # set custom image sizes
        ImageScaling.available_sizes = {'foo': (23,23)}
        # make sure traversing works as expected
        credentials = self.getCredentials()
        response = self.publish('/item/@@images/image/foo', basic=credentials)
        self.assertEqual(response.getStatus(), 200)
        self.assertImage(response.getBody(), 'JPEG', (23, 23))

    def testPublishScaleWithInvalidUID(self):
        scale = self.view.scale('image', width=64, height=64)
        url = scale.url.replace('http://nohost', '')
        # change the url so it's invalid...
        url = url.replace('.jpeg', 'x.jpeg')
        response = self.publish(url, basic=self.getCredentials())
        self.assertEqual(response.getStatus(), 404)

    def testGuardedAccess(self):
        # make sure it's not possible to access scales of forbidden images
        self.item.__allow_access_to_unprotected_subobjects__ = 0
        ImageScaling.available_sizes = {'foo': (23,23)}
        credentials = self.getCredentials()
        response = self.publish('/item/@@images/image/foo', basic=credentials)
        self.assertEqual(response.getStatus(), 401)
        self.item.__allow_access_to_unprotected_subobjects__ = 1

def test_suite():
    from unittest import defaultTestLoader 
    return defaultTestLoader.loadTestsFromName(__name__)
