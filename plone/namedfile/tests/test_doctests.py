import doctest
import unittest
from plone.namedfile.tests.base import setUp
from zope.component.testing import tearDown

def test_suite():
    return unittest.TestSuite([

        doctest.DocFileSuite(
            'usage.txt', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),
        
        doctest.DocFileSuite(
            'handler.txt', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),
        
        doctest.DocFileSuite(
            'marshaler.txt', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),
        
        doctest.DocFileSuite(
            'utils.txt', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),
        
        doctest.DocTestSuite('plone.namedfile.file'),

        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
