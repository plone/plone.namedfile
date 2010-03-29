import os
from Testing.ZopeTestCase import TestCase
from zope.component import testing
from zope.configuration import xmlconfig

def getFile(filename):
    """ return contents of the file with the given name """
    filename = os.path.join(os.path.dirname(__file__), filename)
    return open(filename, 'r')

def setUp(self=None):
    testing.setUp()
    xmlconfig.xmlconfig(getFile('testing.zcml'))

class NamedFileLayer:
    setUp = classmethod(setUp)
    tearDown = classmethod(testing.tearDown)

class NamedFileTestCase(TestCase):
    layer = NamedFileLayer
    def _app(self): # we don't need the app, and it takes forever to load products
        return