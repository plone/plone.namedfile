# -*- coding: utf-8 -*-
from plone.namedfile.testing import PLONE_NAMEDFILE_FUNCTIONAL_TESTING
from plone.testing import layered

import doctest
import re
import six
import unittest


TEST_FILES = [
    'usage.rst',
    'handler.rst',
    'marshaler.rst',
    'utils.rst',
]


class Py23DocChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        if six.PY2:
            got = re.sub("u'(.*?)'", "'\\1'", got)
            got = re.sub('zExceptions.NotFound', 'NotFound', got)
            got = got.replace('bytearray(b', 'bytearray(')
            got = re.sub(
                "WrongType", "zope.schema._bootstrapinterfaces.WrongType", got)
            got = got.replace(
                "filename*=\"utf-8''test.txt\"", "filename*=utf-8''test.txt")

        if six.PY3:
            got = re.sub("b'(.*?)'", "'\\1'", got)
        return doctest.OutputChecker.check_output(self, want, got, optionflags)


def test_suite():
    return unittest.TestSuite(
        [
            layered(
                doctest.DocFileSuite(
                    testfile,
                    package='plone.namedfile',
                    checker=Py23DocChecker(),
                    optionflags=doctest.ELLIPSIS,
                ),
                PLONE_NAMEDFILE_FUNCTIONAL_TESTING,
            ) for testfile in TEST_FILES
        ]

    )


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
