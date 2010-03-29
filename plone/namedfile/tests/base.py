import os
from unittest import TestCase
from zope.component import testing
from zope.configuration import xmlconfig

def getFile(filename):
    """ return contents of the file with the given name """
    filename = os.path.join(os.path.dirname(__file__), filename)
    return open(filename, 'r')

def setUp(self):
    testing.setUp()
    xmlconfig.xmlconfig(getFile('testing.zcml'))
    try:
        self.afterSetUp()
    except AttributeError:
        pass

class NamedFileTestCase(TestCase):
    setUp = setUp
    tearDown = testing.tearDown
