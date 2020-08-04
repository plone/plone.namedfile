# -*- coding: utf-8 -*-
from AccessControl.ZopeGuards import guarded_getattr
from plone.namedfile.utils import set_headers
from plone.namedfile.utils import stream_data
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.Five.browser import BrowserView
from zope.annotation.interfaces import IAnnotations
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound
from ZPublisher.HTTPRangeSupport import expandRanges
from ZPublisher.HTTPRangeSupport import parseRange


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
        request_range = self.handle_request_range(file)
        return stream_data(file, **request_range)

    def handle_request_range(self, file):
        # check if we have a range in the request
        ranges = None
        header_range = self.request.getHeader('Range', None)
        if_range = self.request.getHeader('If-Range', None)
        if header_range is not None:
            ranges = parseRange(header_range)
            if if_range is not None:
                # We delete the ranges, which causes us to skip to the 200
                # response.
                return {}
            # XXX: multipart ranges not implemented
            if ranges and len(ranges) == 1:
                try:
                    length = file.getSize()
                    [(start, end)] = expandRanges(ranges, length)
                    size = end - start
                    self.request.response.setHeader('Content-Length', size)
                    self.request.response.setHeader(
                        'Content-Range',
                        'bytes {0}-{1}/{2}'.format(start, end - 1, length))
                    self.request.response.setStatus(206)  # Partial content
                    return dict(start=start, end=end)
                except ValueError:
                    return {}
        return {}

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
