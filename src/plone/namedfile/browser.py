from AccessControl.ZopeGuards import guarded_getattr
from plone.namedfile.utils import extract_media_type
from plone.namedfile.utils import set_headers
from plone.namedfile.utils import stream_data
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.Five.browser import BrowserView
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound
from ZPublisher.HTTPRangeSupport import expandRanges
from ZPublisher.HTTPRangeSupport import parseRange

import os


# List of mimetypes that we allow to display inline.
# This is mostly to avoid XSS (Cross Site Scripting).
# We especially do not want image/svg+xml, text/html, application/javascript.
# If a Manager has a use case for displaying those inline, there are other ways to create them,
# for example in the ZMI as standard OFS File or maybe via the Resource Registries or Theming control panel.
# ATContentTypes allows PDF and a few old MS Office formats to display inline.
# But I think most browsers always ask what you want to do for each mimetype,
# and you can let it remember your answer.
# So: a few image mimetypes are likely enough here.
# Note: a tag like `<img src="example.svg" />` loading an image/svg+xml mimetype will show up fine.
# But when you visit example.svg as url, you will get a download.
ALLOWED_INLINE_MIMETYPES = [
    "image/gif",
    # The mimetypes registry lists several for jpeg 2000:
    "image/jp2",
    "image/jpeg",
    "image/jpeg2000-image",
    "image/jpeg2000",
    "image/jpx",
    "image/png",
    "image/webp",
    "image/x-icon",
    "image/x-jpeg2000-image",
    "text/plain",
    # By popular request we allow PDF:
    "application/pdf",
]

# Perhaps a denylist is better.
DISALLOWED_INLINE_MIMETYPES = [
    "application/javascript",
    "application/x-javascript",
    "text/javascript",
    "text/html",
    "image/svg+xml",
    "image/svg+xml-compressed",
]

# By default we use the allowlist.  We might change this when merging back to plone.namedfile.
# We give integrators the option to choose the denylist via an environment variable.
try:
    # Look for sane name, and fall back to very specific name of hotfix.
    USE_DENYLIST = os.environ.get(
        "NAMEDFILE_USE_DENYLIST",
        os.environ.get("PLONEHOTFIX20210518_NAMEDFILE_USE_DENYLIST", 0),
    )
    USE_DENYLIST = bool(int(USE_DENYLIST))
except (ValueError, TypeError, AttributeError):
    USE_DENYLIST = False


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
        super().__init__(context, request)
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
        default = {}
        # check if we have a range in the request
        header_range = self.request.getHeader("Range", None)
        if header_range is None:
            return default
        if_range = self.request.getHeader("If-Range", None)
        if if_range is not None:
            # We delete the ranges, which causes us to skip to the 200
            # response.
            return default
        ranges = parseRange(header_range)
        if not ranges or len(ranges) != 1:
            # TODO: multipart ranges not implemented
            return default
        try:
            length = file.getSize()
            [(start, end)] = expandRanges(ranges, length)
            size = end - start
            self.request.response.setHeader("Content-Length", size)
            self.request.response.setHeader(
                "Content-Range", f"bytes {start}-{end - 1}/{length}"
            )
            self.request.response.setStatus(206)  # Partial content
            return dict(start=start, end=end)
        except ValueError:
            return default

    def get_canonical(self, file):
        filename = getattr(file, "filename", None)
        if filename is None:
            return f"{self.context.absolute_url()}/@@download/{self.fieldname}"
        else:
            return (
                f"{self.context.absolute_url()}/@@download/{self.fieldname}/{filename}"
            )

    def set_headers(self, file):
        # With filename None, set_headers will not add the download headers.
        if not self.filename:
            self.filename = getattr(file, "filename", None)
            if self.filename is None:
                self.filename = self.fieldname
                if self.filename is None:
                    self.filename = "file.ext"
        canonical = self.get_canonical(file)
        set_headers(
            file, self.request.response, filename=self.filename, canonical=canonical
        )

    def _getFile(self):
        if not self.fieldname:
            info = IPrimaryFieldInfo(self.context, None)
            if info is None:
                # Ensure that we have at least a fieldname
                raise NotFound(self, "", self.request)
            self.fieldname = info.fieldname

            # respect field level security as defined in plone.autoform
            # check if attribute access would be allowed!
            guarded_getattr(self.context, self.fieldname, None)

            file = info.value
        else:
            context = getattr(self.context, "aq_explicit", self.context)
            file = guarded_getattr(context, self.fieldname, None)

        if file is None:
            raise NotFound(self, self.fieldname, self.request)

        return file


class DisplayFile(Download):
    """Display a file, via ../context/@@display-file/fieldname/filename

    Same as Download, however in this case we don't set the filename so the
    browser can decide to display the file instead.
    """

    # Make the configuration available on the class.
    # Then subclasses can override this.
    allowed_inline_mimetypes = ALLOWED_INLINE_MIMETYPES
    disallowed_inline_mimetypes = DISALLOWED_INLINE_MIMETYPES
    use_denylist = USE_DENYLIST

    def set_headers(self, file):
        if hasattr(file, "contentType"):
            mimetype = extract_media_type(file.contentType)
            if self.use_denylist:
                if mimetype in self.disallowed_inline_mimetypes:
                    # Let the Download view handle this.
                    return super().set_headers(file)
            else:
                # Use the allowlist
                if mimetype not in self.allowed_inline_mimetypes:
                    # Let the Download view handle this.
                    return super().set_headers(file)
        canonical = self.get_canonical(file)
        set_headers(file, self.request.response, canonical=canonical)
