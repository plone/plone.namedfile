import os
from Testing.ZopeTestCase import TestCase, layer
from zope.component import testing
from zope.configuration import xmlconfig

def getFile(filename):
    """ return contents of the file with the given name """
    filename = os.path.join(os.path.dirname(__file__), filename)
    return open(filename, 'r')

def setUp(self=None):
    testing.setUp()
    xmlconfig.xmlconfig(getFile('testing.zcml'))

class NamedFileLayer(layer.ZopeLite):
    setUp = classmethod(setUp)
    tearDown = classmethod(testing.tearDown)

class NamedFileTestCase(TestCase):
    layer = NamedFileLayer
