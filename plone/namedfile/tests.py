import unittest
from zope.testing import doctestunit
from zope.component import testing

def test_suite():
    return unittest.TestSuite([

        doctestunit.DocFileSuite(
            'usage.txt', package='plone.namedfile',
            setUp=testing.setUp, tearDown=testing.tearDown),
        
        doctestunit.DocFileSuite(
            'handler.txt', package='plone.namedfile',
            setUp=testing.setUp, tearDown=testing.tearDown),
        
        doctestunit.DocFileSuite(
            'marshaler.txt', package='plone.namedfile',
            setUp=testing.setUp, tearDown=testing.tearDown),
        
        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
