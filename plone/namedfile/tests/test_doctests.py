import unittest
from zope.testing import doctestunit
from plone.namedfile.tests.base import setUp
from zope.component.testing import tearDown

def test_suite():
    return unittest.TestSuite([

        doctestunit.DocFileSuite(
            'usage.txt', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),
        
        doctestunit.DocFileSuite(
            'handler.txt', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),
        
        doctestunit.DocFileSuite(
            'marshaler.txt', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),
        
        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
