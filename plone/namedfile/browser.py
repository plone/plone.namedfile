# -*- coding: utf-8 -*-
from AccessControl.ZopeGuards import guarded_getattr
from plone.namedfile.utils import set_headers
from plone.namedfile.utils import stream_data
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.Five.browser import BrowserView
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound


@implementer(IPublishTraverse)
class Download(BrowserView):
    """Download a file, via ../context/@@download/fieldname/filename

    `fieldname` is the name of an attribute on the context that contains
    the file. `filename` is the filename that the browser will be told to
    give the file. If not given, it will be looked up from the field.

    The attribute under `fieldname` should contain a named (blob) file/image
    instance from this package.

    If no `fieldname` is supplied, then a default field is looked up through
    adaption to `plone.rfc822.interfaces.IPrimaryFieldInfo`.
    """

    def __init__(self, context, request):
        super(Download, self).__init__(context, request)
        self.fieldname = None
        self.filename = None

    def publishTraverse(self, request, name):

        if self.fieldname is None:  # ../@@download/fieldname
            self.fieldname = name
        elif self.filename is None:  # ../@@download/fieldname/filename
            self.filename = name
        else:
            raise NotFound(self, name, request)

        return self

    def __call__(self):
        file = self._getFile()
        self.set_headers(file)
        return stream_data(file)

    def set_headers(self, file):
        if not self.filename:
            self.filename = getattr(file, 'filename', self.fieldname)
        set_headers(file, self.request.response, filename=self.filename)

    def _getFile(self):
        if not self.fieldname:
            info = IPrimaryFieldInfo(self.context, None)
            if info is None:
                # Ensure that we have at least a fieldname
                raise NotFound(self, '', self.request)
            self.fieldname = info.fieldname

            # respect field level security as defined in plone.autoform
            # check if attribute access would be allowed!
            guarded_getattr(self.context, self.fieldname, None)

            file = info.value
        else:
            context = getattr(self.context, 'aq_explicit', self.context)
            file = guarded_getattr(context, self.fieldname, None)

        if file is None:
            raise NotFound(self, self.fieldname, self.request)

        return file


class DisplayFile(Download):
    """Display a file, via ../context/@@display-file/fieldname/filename

    Same as Download, however in this case we don't set the filename so the
    browser can decide to display the file instead.
    """
    def set_headers(self, file):
        set_headers(file, self.request.response)
