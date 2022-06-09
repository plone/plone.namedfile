# -*- coding: utf-8 -*-
from plone.namedfile.file import NamedBlobFile  # noqa
from plone.namedfile.file import NamedBlobImage  # noqa
from plone.namedfile.file import NamedFile  # noqa
from plone.namedfile.file import NamedImage  # noqa


# XXX: this is a temporary monkey patch for testing 
# https://github.com/plone/plone.namedfile/pull/117
from plone.scale.storage import AnnotationStorage
from zope.annotation import IAnnotations
from plone.scale.storage import  ScalesDict
from plone.protect.auto import safeWrite


def _storage(self):
    annotations = IAnnotations(self.context)
    if "plone.scale" not in annotations:
        annotations["plone.scale"] = ScalesDict()
        safeWrite(self.context)
    scales = annotations["plone.scale"]
    if not isinstance(scales, ScalesDict):
        # migrate from PersistentDict to ScalesDict
        new_scales = ScalesDict(scales)
        annotations["plone.scale"] = new_scales
        safeWrite(self.context)
        return new_scales
    return scales

AnnotationStorage.storage = property(_storage)
