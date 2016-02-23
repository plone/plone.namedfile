# -*- coding: utf-8 -*-
from plone.namedfile.tests.base import setUp
from zope.component.testing import tearDown

import doctest
import unittest


def test_suite():
    return unittest.TestSuite([

        doctest.DocFileSuite(
            'usage.rst', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),

        doctest.DocFileSuite(
            'handler.rst', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),

        doctest.DocFileSuite(
            'marshaler.rst', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),

        doctest.DocFileSuite(
            'utils.rst', package='plone.namedfile',
            setUp=setUp, tearDown=tearDown),

        doctest.DocTestSuite('plone.namedfile.file'),

    ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
