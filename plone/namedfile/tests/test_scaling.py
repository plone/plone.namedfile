import re
from DateTime import DateTime
from OFS.SimpleItem import SimpleItem

from plone.namedfile.tests.base import NamedFileTestCase, getFile
from plone.namedfile.tests.base import NamedFileFunctionalTestCase

from zope.annotation import IAttributeAnnotatable
from zope.interface import implements
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.namedfile.field import NamedImage as NamedImageField
from plone.namedfile.file import NamedImage
from plone.namedfile.scaling import ImageScaling

class IHasImage(IImageScaleTraversable):
    image = NamedImageField()

class DummyContent(SimpleItem):
    implements(IAttributeAnnotatable, IHasImage)
    image = None
    modified = DateTime
    def absolute_url(self):
        return 'http://dummy'
    def Title(self):
        return self.title

class ImageScalingTests(NamedFileTestCase):

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
        expected_url = re.compile(r'http://dummy/@@images/[-a-z0-9]{36}\.jpeg')
        self.failUnless(expected_url.match(foo.absolute_url()))
        self.assertEqual(foo.url, foo.absolute_url())
        # XXX
#        self.assertEqual(foo.tag(), '')

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

class ImageTraverseTests(NamedFileTestCase):

    def afterSetUp(self):
        data = getFile('image.gif').read()
        item = DummyContent()
        item.title = 'foo'
        item.image = NamedImage(data, 'image/gif', 'image.gif')
        self.app._setOb('item', item)
        self.item = self.app.item

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
        uid, ext, width, height = self.traverse('image/thumb')
        self.assertEqual((width, height), ImageScaling.available_sizes['thumb'])
        self.assertEqual(ext, 'jpeg')

    def testCustomSizes(self):
        # set custom image sizes
        ImageScaling.available_sizes['foo'] = (23,23)
        # make sure traversing works with the new sizes
        uid, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 23)
        self.assertEqual(height, 23)

    def testScaleInvalidation(self):
        # first view the thumbnail of the original image
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
        ImageScaling.available_sizes['foo'] = (23,23)
        uid1, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 23)
        self.assertEqual(height, 23)
        # now let's update the scale dimensions, after which the scale
        # should also have been updated...
        ImageScaling.available_sizes['foo'] = (42,42)
        uid2, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 42)
        self.assertEqual(height, 42)
        self.assertNotEqual(uid1, uid2, 'scale not updated?')


# class ImagePublisherTests(NamedFileFunctionalTestCase):
# 
#     def afterSetUp(self):
#         data = self.getImage()
#         folder = self.folder
#         foo = folder[folder.invokeFactory('Image', id='foo', image=data)]
#         self.view = foo.unrestrictedTraverse('@@images')
# 
#     def testPublishScaleViaUID(self):
#         scale = self.view.scale('image', width=64, height=64)
#         # make sure the referenced image scale is available
#         url = scale.url.replace('http://nohost', '')
#         response = self.publish(url, basic=self.getCredentials())
#         self.assertEqual(response.getStatus(), 200)
#         self.assertEqual(response.getHeader('Content-Type'), 'image/jpeg')
#         self.assertImage(response.getBody(), 'JPEG', (64, 64))
# 
#     def testPublishThumbViaUID(self):
#         scale = self.view.scale('image', 'thumb')
#         # make sure the referenced image scale is available
#         url = scale.url.replace('http://nohost', '')
#         response = self.publish(url, basic=self.getCredentials())
#         self.assertEqual(response.getStatus(), 200)
#         self.assertEqual(response.getHeader('Content-Type'), 'image/jpeg')
#         self.assertImage(response.getBody(), 'JPEG', (128, 128))
# 
#     def testPublishCustomSizeViaUID(self):
#         # set custom image sizes
#         iprops = self.portal.portal_properties.imaging_properties
#         iprops.manage_changeProperties(allowed_sizes=['foo 23:23'])
#         scale = self.view.scale('image', 'foo')
#         # make sure the referenced image scale is available
#         url = scale.url.replace('http://nohost', '')
#         response = self.publish(url, basic=self.getCredentials())
#         self.assertEqual(response.getStatus(), 200)
#         self.assertEqual(response.getHeader('Content-Type'), 'image/jpeg')
#         self.assertImage(response.getBody(), 'JPEG', (23, 23))
# 
#     def testPublishThumbViaName(self):
#         # make sure traversing works as is and with scaling
#         base = '/'.join(self.folder.getPhysicalPath())
#         credentials = self.getCredentials()
#         # first the field without a scale name
#         response = self.publish(base + '/foo/@@images/image', basic=credentials)
#         self.assertEqual(response.getStatus(), 200)
#         self.assertEqual(response.getBody(), self.getImage())
#         self.assertEqual(response.getHeader('Content-Type'), 'image/gif')
#         # and last a scaled version
#         response = self.publish(base + '/foo/@@images/image/thumb', basic=credentials)
#         self.assertEqual(response.getStatus(), 200)
#         self.assertEqual(response.getHeader('Content-Type'), 'image/jpeg')
#         self.assertImage(response.getBody(), 'JPEG', (128, 128))
# 
#     def testPublishCustomSizeViaName(self):
#         # set custom image sizes
#         iprops = self.portal.portal_properties.imaging_properties
#         iprops.manage_changeProperties(allowed_sizes=['foo 23:23'])
#         # make sure traversing works as expected
#         base = '/'.join(self.folder.getPhysicalPath())
#         credentials = self.getCredentials()
#         response = self.publish(base + '/foo/@@images/image/foo', basic=credentials)
#         self.assertEqual(response.getStatus(), 200)
#         self.assertImage(response.getBody(), 'JPEG', (23, 23))

def test_suite():
    from unittest import defaultTestLoader 
    return defaultTestLoader.loadTestsFromName(__name__)
