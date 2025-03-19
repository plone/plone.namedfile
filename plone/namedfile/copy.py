"""Copy hook for proper copying blob data

This file was borrowed from z3c.blobfile and is licensed under the terms of
the ZPL.
"""

from plone.namedfile.interfaces import INamedBlobFile
from ZODB.blob import Blob
from zope.component import adapter
from zope.copy.interfaces import ICopyHook
from zope.copy.interfaces import ResumeCopy
from zope.interface import implementer

import shutil


@implementer(ICopyHook)
@adapter(INamedBlobFile)
class BlobFileCopyHook:
    """A copy hook that fixes the blob after copying"""

    def __init__(self, context):
        self.context = context

    def __call__(self, toplevel, register):
        register(self._copyBlob)
        raise ResumeCopy

    def _copyBlob(self, translate):
        target = translate(self.context)
        target._blob = Blob()
        fsrc = self.context._blob.open("r")
        fdst = target._blob.open("w")
        shutil.copyfileobj(fsrc, fdst)
        fdst.close()
        fsrc.close()
