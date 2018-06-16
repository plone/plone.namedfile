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
            got = re.sub('zExceptions.NotFound', 'NotFound', got)
            got = re.sub("u'(.*?)'", "'\\1'", got)
            got = re.sub(
                r"WrongType: \('(.*?)', <type 'unicode'>, '(.*?)'\)",
                r"zope.schema._bootstrapinterfaces.WrongType: (b'\1', <class 'str'>, '\2')",    # noqa E508
                got
            )
        return doctest.OutputChecker.check_output(self, want, got, optionflags)


def test_suite():
    return unittest.TestSuite(
        [
            layered(
                doctest.DocFileSuite(
                    testfile,
                    package='plone.namedfile',
                    checker=Py23DocChecker(),
                ),
                PLONE_NAMEDFILE_FUNCTIONAL_TESTING
            ) for testfile in TEST_FILES
        ]

    )


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
