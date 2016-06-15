# -*- coding: utf-8 -*-
from StringIO import StringIO
from Testing import ZopeTestCase as ztc
from Testing.testbrowser import Browser
from zope.component import testing
from zope.configuration import xmlconfig

import os
import PIL.Image


def getFile(filename):
    """ return contents of the file with the given name """
    filename = os.path.join(os.path.dirname(__file__), filename)
    return open(filename, 'rb')


def setUp(self=None):
    testing.setUp()
    xmlconfig.xmlconfig(getFile('testing.zcml'))


class NamedFileLayer:
    setUp = classmethod(setUp)
    tearDown = classmethod(testing.tearDown)

try:
    from Testing.ZopeTestCase.layer import ZopeLite
except ImportError:
    pass
else:
    NamedFileLayer.__bases__ = (ZopeLite,)


class ImageTestMixin(object):

    def assertImage(self, data, format_, size):
        image = PIL.Image.open(StringIO(data))
        self.assertEqual(image.format, format_)
        self.assertEqual(image.size, size)


class NamedFileTestCase(ztc.TestCase, ImageTestMixin):
    layer = NamedFileLayer


class NamedFileFunctionalTestCase(
        ztc.Functional,
        ztc.ZopeTestCase,
        ImageTestMixin):
    layer = NamedFileLayer

    def getCredentials(self):
        return u'{0}:{0}'.format(ztc.user_name, ztc.user_password)

    def getBrowser(self, loggedIn=True):
        """ instantiate and return a testbrowser for convenience """
        browser = Browser()
        if loggedIn:
            auth = u'Basic {0}'.format(self.getCredentials())
            browser.addHeader('Authorization', auth)
        return browser
