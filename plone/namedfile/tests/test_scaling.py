# -*- coding: utf-8 -*-
from DateTime import DateTime
from OFS.SimpleItem import SimpleItem
from plone.namedfile.field import NamedImage as NamedImageField
from plone.namedfile.file import NamedImage
from plone.namedfile.interfaces import IAvailableSizes
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.namedfile.scaling import ImageScaling
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.namedfile.testing import PLONE_NAMEDFILE_INTEGRATION_TESTING
from plone.namedfile.tests import getFile
from plone.scale.interfaces import IScaledImageQuality
from six import BytesIO
from zExceptions import Unauthorized
from zope.annotation import IAttributeAnnotatable
from zope.component import getGlobalSiteManager
from zope.component import getSiteManager
from zope.interface import implementer

import PIL
import re
import time
import unittest


def wait_to_ensure_modified():
    # modified is measured in milliseconds
    # wait 5ms to ensure modified will have changed
    time.sleep(0.005)


class IHasImage(IImageScaleTraversable):
    image = NamedImageField()


def assertImage(testcase, data, format_, size):
    image = PIL.Image.open(BytesIO(data))
    testcase.assertEqual(image.format, format_)
    testcase.assertEqual(image.size, size)


@implementer(IAttributeAnnotatable, IHasImage)
class DummyContent(SimpleItem):
    image = None
    modified = DateTime
    id = __name__ = 'item'
    title = 'foo'

    def Title(self):
        return self.title


class MockNamedImage(NamedImage):
    _p_mtime = DateTime().millis()


@implementer(IScaledImageQuality)
class DummyQualitySupplier(object):
    """ fake utility for plone.app.imaging's scaling quality """

    def getQuality(self):
        return 1  # as bad as it gets


class ImageScalingTests(unittest.TestCase):

    layer = PLONE_NAMEDFILE_INTEGRATION_TESTING

    def setUp(self):
        data = getFile('image.png')
        item = DummyContent()
        item.image = MockNamedImage(data, 'image/png', u'image.png')
        self.layer['app']._setOb('item', item)
        self.item = self.layer['app'].item
        self.scaling = ImageScaling(self.item, None)

    def testCreateScale(self):
        foo = self.scaling.scale('image', width=100, height=80)
        self.assertTrue(foo.uid)
        self.assertEqual(foo.mimetype, 'image/png')
        self.assertIsInstance(foo.mimetype, str)
        self.assertEqual(foo.data.contentType, 'image/png')
        self.assertIsInstance(foo.data.contentType, str)
        self.assertEqual(foo.width, 80)
        self.assertEqual(foo.height, 80)
        assertImage(self, foo.data.data, 'PNG', (80, 80))

    def testCreateExactScale(self):
        foo = self.scaling.scale('image', width=100, height=80)
        self.assertIsNot(foo.data, self.item.image)

        # test that exact scale without parameters returns original
        foo = self.scaling.scale('image',
                                 width=self.item.image._width,
                                 height=self.item.image._height)
        self.assertIs(foo.data, self.item.image)

        foo = self.scaling.scale('image',
                                 width=self.item.image._width,
                                 height=self.item.image._height,
                                 quality=80)
        self.assertIsNot(foo.data, self.item.image)

    def testCreateHighPixelDensityScale(self):
        self.scaling.getHighPixelDensityScales = lambda: [{'scale': 2, 'quality': 66}]
        foo = self.scaling.scale('image', width=100, height=80)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]['mimetype'], 'image/png')
        self.assertEqual(foo.srcset[0]['height'], 160)
        self.assertEqual(foo.srcset[0]['width'], 160)
        assertImage(self, foo.srcset[0]['data'].data, 'PNG', (160, 160))

    def testCreateScaleWithoutData(self):
        item = DummyContent()
        scaling = ImageScaling(item, None)
        foo = scaling.scale('image', width=100, height=80)
        self.assertEqual(foo, None)

    def testCreateHighPixelDensityScaleWithoutData(self):
        item = DummyContent()
        scaling = ImageScaling(item, None)
        scaling.getHighPixelDensityScales = lambda: [{'scale': 2, 'quality': 66}]
        foo = scaling.scale('image', width=100, height=80)
        self.assertFalse(hasattr(foo, 'srcset'))

    def testGetScaleByName(self):
        self.scaling.available_sizes = {'foo': (60, 60)}
        foo = self.scaling.scale('image', scale='foo')
        self.assertTrue(foo.uid)
        self.assertEqual(foo.mimetype, 'image/png')
        self.assertIsInstance(foo.mimetype, str)
        self.assertEqual(foo.data.contentType, 'image/png')
        self.assertIsInstance(foo.data.contentType, str)
        self.assertEqual(foo.width, 60)
        self.assertEqual(foo.height, 60)
        assertImage(self, foo.data.data, 'PNG', (60, 60))
        expected_url = re.compile(
            r'http://nohost/item/@@images/[-a-z0-9]{36}\.png')
        self.assertTrue(expected_url.match(foo.absolute_url()))
        self.assertEqual(foo.url, foo.absolute_url())

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = \
            r'<img src="{0}/@@images/([-0-9a-f]{{36}}).(jpeg|gif|png)" ' \
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" />'.format(
                base,
            )
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetHighPixelDensityScaleByName(self):
        self.scaling.getHighPixelDensityScales = lambda: [{'scale': 2, 'quality': 66}]
        self.scaling.available_sizes = {'foo': (60, 60)}
        foo = self.scaling.scale('image', scale='foo')
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]['mimetype'], 'image/png')
        self.assertEqual(foo.srcset[0]['width'], 120)
        self.assertEqual(foo.srcset[0]['height'], 120)
        assertImage(self, foo.srcset[0]['data'].data, 'PNG', (120, 120))

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            r'<img src="{0}'.format(base) +
            r'/@@images/([-0-9a-f]{36})'
            r'.(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" '
            r'srcset="http://nohost/item/@@images/([-0-9a-f]{36})'
            r'.(jpeg|gif|png)'
            r' 2x" />')
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetRetinaScaleByWidthAndHeight(self):
        self.scaling.getHighPixelDensityScales = lambda: [{'scale': 2, 'quality': 66}]
        foo = self.scaling.scale('image', width=60, height=60)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]['mimetype'], 'image/png')
        self.assertEqual(foo.srcset[0]['width'], 120)
        self.assertEqual(foo.srcset[0]['height'], 120)
        assertImage(self, foo.srcset[0]['data'].data, 'PNG', (120, 120))

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            r'<img src="{0}'.format(base) +
            r'/@@images/([-0-9a-f]{36})'
            r'.(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" '
            r'srcset="http://nohost/item/@@images/([-0-9a-f]{36})'
            r'.(jpeg|gif|png)'
            r' 2x" />')
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetRetinaScaleByWidthOnly(self):
        self.scaling.getHighPixelDensityScales = lambda: [{'scale': 2, 'quality': 66}]
        foo = self.scaling.scale('image', width=60)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]['mimetype'], 'image/png')
        self.assertEqual(foo.srcset[0]['width'], 120)
        self.assertEqual(foo.srcset[0]['height'], 120)
        assertImage(self, foo.srcset[0]['data'].data, 'PNG', (120, 120))

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            r'<img src="{0}'.format(base) +
            r'/@@images/([-0-9a-f]{36})'
            r'.(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" '
            r'srcset="http://nohost/item/@@images/([-0-9a-f]{36})'
            r'.(jpeg|gif|png)'
            r' 2x" />')
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetRetinaScaleByHeightOnly(self):
        self.scaling.getHighPixelDensityScales = lambda: [{'scale': 2, 'quality': 66}]
        foo = self.scaling.scale('image', height=60)
        self.assertTrue(foo.srcset)
        self.assertEqual(foo.srcset[0]['mimetype'], 'image/png')
        self.assertEqual(foo.srcset[0]['width'], 120)
        self.assertEqual(foo.srcset[0]['height'], 120)
        assertImage(self, foo.srcset[0]['data'].data, 'PNG', (120, 120))

        tag = foo.tag()
        base = self.item.absolute_url()
        expected = (
            r'<img src="{0}'.format(base) +
            r'/@@images/([-0-9a-f]{36})'
            r'.(jpeg|gif|png)" '
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" '
            r'srcset="http://nohost/item/@@images/([-0-9a-f]{36})'
            r'.(jpeg|gif|png)'
            r' 2x" />')
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)

    def testGetUnknownScale(self):
        foo = self.scaling.scale('image', scale='foo?')
        self.assertEqual(foo, None)

    def testScaleInvalidation(self):
        dt = self.item.modified()

        # Test that different parameters give different scale
        self.item.modified = lambda: dt
        self.item.image._p_mtime = dt.millis()
        scale1a = self.scaling.scale('image', width=100, height=80)
        scale2a = self.scaling.scale('image', width=80, height=60)
        self.assertNotEqual(scale1a.data, scale2a.data)

        # Test that bare object modification does not invalidate scales
        self.item.modified = lambda: dt + 1
        scale1b = self.scaling.scale('image', width=100, height=80)
        scale2b = self.scaling.scale('image', width=80, height=60)
        self.assertNotEqual(scale1b.data, scale2b.data)
        self.assertEqual(scale1a.data, scale1b.data)
        self.assertEqual(scale2a.data, scale2b.data)

        # Test that field modification invalidates scales
        self.item.image._p_mtime = (dt + 1).millis()
        scale1b = self.scaling.scale('image', width=100, height=80)
        scale2b = self.scaling.scale('image', width=80, height=60)
        self.assertNotEqual(scale1b.data, scale2b.data)
        self.assertNotEqual(scale1a.data, scale1b.data, 'scale not updated?')
        self.assertNotEqual(scale2a.data, scale2b.data, 'scale not updated?')

    def testCustomSizeChange(self):
        # set custom image sizes & view a scale
        self.scaling.available_sizes = {'foo': (23, 23)}
        foo = self.scaling.scale('image', scale='foo')
        self.assertEqual(foo.width, 23)
        self.assertEqual(foo.height, 23)
        # now let's update the scale dimensions, after which the scale
        # shouldn't be the same...
        self.scaling.available_sizes = {'foo': (42, 42)}
        foo = self.scaling.scale('image', scale='foo')
        self.assertEqual(foo.width, 42)
        self.assertEqual(foo.height, 42)

    def testAvailableSizes(self):
        # by default, no named scales are configured
        self.assertEqual(self.scaling.available_sizes, {})

        # a callable can be used to look up the available sizes
        def custom_available_sizes():
            return {'bar': (10, 10)}
        sm = getSiteManager()
        sm.registerUtility(component=custom_available_sizes,
                           provided=IAvailableSizes)
        self.assertEqual(self.scaling.available_sizes, {'bar': (10, 10)})
        sm.unregisterUtility(provided=IAvailableSizes)
        # for testing purposes, the sizes may also be set directly on
        # the scaling adapter
        self.scaling.available_sizes = {'qux': (12, 12)}
        self.assertEqual(self.scaling.available_sizes, {'qux': (12, 12)})

    def testGuardedAccess(self):
        # make sure it's not possible to access scales of forbidden images
        self.item.__allow_access_to_unprotected_subobjects__ = 0
        self.assertRaises(Unauthorized,
                          self.scaling.guarded_orig_image, 'image')
        self.item.__allow_access_to_unprotected_subobjects__ = 1

    def testGetAvailableSizes(self):
        self.scaling.available_sizes = {'foo': (60, 60)}
        assert self.scaling.getAvailableSizes('image') == {'foo': (60, 60)}

    def testGetImageSize(self):
        assert self.scaling.getImageSize('image') == (200, 200)

    def testGetOriginalScaleTag(self):
        tag = self.scaling.tag('image')
        base = self.item.absolute_url()
        expected = \
            r'<img src="{0}/@@images/([-0-9a-f]{{36}}).(jpeg|gif|png)" ' \
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" />'.format(
                base,
            )
        self.assertTrue(re.match(expected, tag).groups())

    def testScaleOnItemWithNonASCIITitle(self):
        self.item.title = u'ü'
        tag = self.scaling.tag('image')
        base = self.item.absolute_url()
        expected = \
            r'<img src="{0}/@@images/([-0-9a-f]{{36}}).(jpeg|gif|png)" ' \
            r'alt="\xfc" title="\xfc" height="(\d+)" width="(\d+)" />'.format(
                base,
            )
        self.assertTrue(re.match(expected, tag).groups())

    def testScaleOnItemWithUnicodeTitle(self):
        self.item.Title = lambda: u'ü'
        tag = self.scaling.tag('image')
        base = self.item.absolute_url()
        expected = \
            r'<img src="{0}/@@images/([-0-9a-f]{{36}}).(jpeg|gif|png)" ' \
            r'alt="\xfc" title="\xfc" height="(\d+)" width="(\d+)" />'.format(
                base,
            )
        self.assertTrue(re.match(expected, tag).groups())

    def testScaledJpegImageQuality(self):
        """Test image quality setting for jpeg images.
        Image quality not available for PNG images.
        """
        data = getFile('image.jpg')
        item = DummyContent()
        item.image = NamedImage(data, 'image/png', u'image.jpg')
        scaling = ImageScaling(item, None)

        # scale an image, record its size
        foo = scaling.scale('image', width=100, height=80)
        size_foo = foo.data.getSize()
        # let's pretend p.a.imaging set the scaling quality to "really sloppy"
        gsm = getGlobalSiteManager()
        qualitySupplier = DummyQualitySupplier()
        gsm.registerUtility(qualitySupplier.getQuality, IScaledImageQuality)
        wait_to_ensure_modified()
        # now scale again
        bar = scaling.scale('image', width=100, height=80)
        size_bar = bar.data.getSize()
        # first one should be bigger
        self.assertTrue(size_foo > size_bar)

    def testOversizedHighPixelDensityScale(self):
        orig_size = max(self.scaling.getImageSize('image'))
        scale_size = orig_size / 2
        self.scaling.getHighPixelDensityScales = lambda: [
            {'scale': 2, 'quality': 66},
            {'scale': 3, 'quality': 66}]
        foo = self.scaling.scale('image', width=scale_size, height=scale_size)
        self.assertEqual(len(foo.srcset), 1)
        self.assertEqual(foo.srcset[0]['scale'], 2)

    def testImgSrcSet(self):
        """test rendered srcset values"""
        self.scaling.available_sizes = {
            "huge": (1600, 65536),
            "great": (1200, 65536),
            "larger": (1000, 65536),
            "large": (800, 65536),
            "teaser": (600, 65536),
            "preview": (400, 65536),
            "mini": (200, 65536),
            "thumb": (128, 128),
            "tile": (64, 64),
            "icon": (32, 32),
            "listing": (16, 16),
        }
        tag = self.scaling.srcset("image", sizes="50vw")
        base = self.item.absolute_url()
        expected = f"""<img title="foo" alt="foo" sizes="50vw" srcset="{base}/@@images/image-200-....png 200w, {base}/@@images/image-128-....png 128w, {base}/@@images/image-64-....png 64w, {base}/@@images/image-32-....png 32w, {base}/@@images/image-16-....png 16w" src="{base}/@@images/image-1600-....png".../>"""
        self.assertTrue(_ellipsis_match(expected, tag.strip()))

    def testImgSrcSetCustomSrc(self):
        """test that we can select a custom scale in the src attribute"""
        self.scaling.available_sizes = {
            "huge": (1600, 65536),
            "great": (1200, 65536),
            "larger": (1000, 65536),
            "large": (800, 65536),
            "teaser": (600, 65536),
            "preview": (400, 65536),
            "mini": (200, 65536),
            "thumb": (128, 128),
            "tile": (64, 64),
            "icon": (32, 32),
            "listing": (16, 16),
        }
        tag = self.scaling.srcset("image", sizes="50vw", scale_in_src="mini")
        base = self.item.absolute_url()
        expected = f"""<img title="foo" alt="foo" sizes="50vw" srcset="{base}/@@images/image-200-....png 200w, {base}/@@images/image-128-....png 128w, {base}/@@images/image-64-....png 64w, {base}/@@images/image-32-....png 32w, {base}/@@images/image-16-....png 16w" src="{base}/@@images/image-200-....png".../>"""
        self.assertTrue(_ellipsis_match(expected, tag.strip()))

    def testImgSrcSetInexistentScale(self):
        """test that when requesting an inexistent scale for the src attribute
        we provide the biggest scale we can produce
        """
        self.scaling.available_sizes = {
            "huge": (1600, 65536),
            "great": (1200, 65536),
            "larger": (1000, 65536),
            "large": (800, 65536),
            "teaser": (600, 65536),
            "preview": (400, 65536),
            "mini": (200, 65536),
            "thumb": (128, 128),
            "tile": (64, 64),
            "icon": (32, 32),
            "listing": (16, 16),
        }
        tag = self.scaling.srcset(
            "image", sizes="50vw", scale_in_src="inexistent-scale-name"
        )
        base = self.item.absolute_url()
        expected = f"""<img title="foo" alt="foo" sizes="50vw" srcset="{base}/@@images/image-200-....png 200w, {base}/@@images/image-128-....png 128w, {base}/@@images/image-64-....png 64w, {base}/@@images/image-32-....png 32w, {base}/@@images/image-16-....png 16w" src="{base}/@@images/image-200-....png".../>"""
        self.assertTrue(_ellipsis_match(expected, tag.strip()))

    def testImgSrcSetCustomTitle(self):
        """test passing a custom title to the srcset method"""
        self.scaling.available_sizes = {
            "huge": (1600, 65536),
            "great": (1200, 65536),
            "larger": (1000, 65536),
            "large": (800, 65536),
            "teaser": (600, 65536),
            "preview": (400, 65536),
            "mini": (200, 65536),
            "thumb": (128, 128),
            "tile": (64, 64),
            "icon": (32, 32),
            "listing": (16, 16),
        }
        tag = self.scaling.srcset("image", sizes="50vw", title="My Custom Title")
        base = self.item.absolute_url()
        expected = f"""<img title="My Custom Title" alt="foo" sizes="50vw" srcset="{base}/@@images/image-200-....png 200w, {base}/@@images/image-128-....png 128w, {base}/@@images/image-64-....png 64w, {base}/@@images/image-32-....png 32w, {base}/@@images/image-16-....png 16w" src="{base}/@@images/image-1600-....png".../>"""
        self.assertTrue(_ellipsis_match(expected, tag.strip()))

    def testImgSrcSetAdditionalAttributes(self):
        """test that additional parameters are output as is, like alt, loading, ..."""
        self.scaling.available_sizes = {
            "huge": (1600, 65536),
            "great": (1200, 65536),
            "larger": (1000, 65536),
            "large": (800, 65536),
            "teaser": (600, 65536),
            "preview": (400, 65536),
            "mini": (200, 65536),
            "thumb": (128, 128),
            "tile": (64, 64),
            "icon": (32, 32),
            "listing": (16, 16),
        }
        tag = self.scaling.srcset(
            "image",
            sizes="50vw",
            alt="This image shows nothing",
            css_class="my-personal-class",
            title="My Custom Title",
            loading="lazy",
        )
        base = self.item.absolute_url()

        expected = f"""<img title="My Custom Title" alt="This image shows nothing" class="my-personal-class" loading="lazy" sizes="50vw" srcset="{base}/@@images/image-200-....png 200w, {base}/@@images/image-128-....png 128w, {base}/@@images/image-64-....png 64w, {base}/@@images/image-32-....png 32w, {base}/@@images/image-16-....png 16w" src="{base}/@@images/image-1600-....png".../>"""
        self.assertTrue(_ellipsis_match(expected, tag.strip()))


class ImageTraverseTests(unittest.TestCase):

    layer = PLONE_NAMEDFILE_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        data = getFile('image.png')
        item = DummyContent()
        item.image = NamedImage(data, 'image/png', u'image.png')
        self.app._setOb('item', item)
        self.item = self.app.item
        self._orig_sizes = ImageScaling._sizes

    def tearDown(self):
        ImageScaling._sizes = self._orig_sizes

    def traverse(self, path=''):
        view = self.item.unrestrictedTraverse('@@images')
        stack = path.split('/')
        name = stack.pop(0)
        static_traverser = view.traverse(name, stack)
        scale = stack.pop(0)
        tag = static_traverser.traverse(scale, stack)
        base = self.item.absolute_url()
        expected = \
            r'<img src="{0}/@@images/([-0-9a-f]{{36}}).(jpeg|gif|png)" ' \
            r'alt="foo" title="foo" height="(\d+)" width="(\d+)" />'.format(
                base,
            )
        groups = re.match(expected, tag).groups()
        self.assertTrue(groups, tag)
        uid, ext, height, width = groups
        return uid, ext, int(width), int(height)

    def testImageThumb(self):
        ImageScaling._sizes = {'thumb': (128, 128)}
        uid, ext, width, height = self.traverse('image/thumb')
        self.assertEqual((width, height), ImageScaling._sizes['thumb'])
        self.assertEqual(ext, 'png')

    def testCustomSizes(self):
        # set custom image sizes
        ImageScaling._sizes = {'foo': (23, 23)}
        # make sure traversing works with the new sizes
        uid, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 23)
        self.assertEqual(height, 23)

    def testScaleInvalidation(self):
        # first view the thumbnail of the original image
        ImageScaling._sizes = {'thumb': (128, 128)}
        uid1, ext, width1, height1 = self.traverse('image/thumb')
        wait_to_ensure_modified()
        # now upload a new one and make sure the thumbnail has changed
        data = getFile('image.jpg')
        self.item.image = NamedImage(data, 'image/jpeg', u'image.jpg')
        uid2, ext, width2, height2 = self.traverse('image/thumb')
        self.assertNotEqual(uid1, uid2, 'thumb not updated?')
        # the height also differs as the original image had a size of 200, 200
        # whereas the updated one has 500, 200...
        self.assertEqual(width1, width2)
        self.assertNotEqual(height1, height2)

    def testCustomSizeChange(self):
        # set custom image sizes & view a scale
        ImageScaling._sizes = {'foo': (23, 23)}
        uid1, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 23)
        self.assertEqual(height, 23)
        # now let's update the scale dimensions, after which the scale
        # should also have been updated...
        ImageScaling._sizes = {'foo': (42, 42)}
        uid2, ext, width, height = self.traverse('image/foo')
        self.assertEqual(width, 42)
        self.assertEqual(height, 42)
        self.assertNotEqual(uid1, uid2, 'scale not updated?')

    def testGuardedAccess(self):
        # make sure it's not possible to access scales of forbidden images
        self.item.__allow_access_to_unprotected_subobjects__ = 0
        ImageScaling._sizes = {'foo': (42, 42)}
        self.assertRaises(Unauthorized, self.traverse, 'image/foo')
        self.item.__allow_access_to_unprotected_subobjects__ = 1


def test_suite():
    from unittest import defaultTestLoader
    return defaultTestLoader.loadTestsFromName(__name__)
