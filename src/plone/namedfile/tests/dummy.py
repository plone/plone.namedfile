from io import BytesIO
from ZPublisher.HTTPRequest import FileUpload

import os


GIF_FILE = os.path.join(os.path.dirname(__file__), "tool.gif")
with open(GIF_FILE, "rb") as f:
    GIF = f.read()
# jpeg file of 900x900 pixels
JPEG_FILE = os.path.join(os.path.dirname(__file__), "900.jpg")
with open(JPEG_FILE, "rb") as f:
    JPEG = f.read()


class File(FileUpload):
    """Dummy upload object
    Used to fake uploaded files.
    """

    __allow_access_to_unprotected_subobjects__ = 1
    filename = "dummy.txt"
    data = b"file data"
    headers = {}

    def __init__(self, filename=None, data=None, headers=None):
        if filename is not None:
            self.filename = filename
        if data is not None:
            self.data = data
        if headers is not None:
            self.headers = headers
        self.file = BytesIO(self.data)

    def seek(self, *args):
        pass

    def tell(self, *args):
        return 1

    def read(self, *args):
        return self.data


class Image(File):
    """Dummy image upload object
    Contains valid image data by default.
    """

    filename = "dummy.gif"
    data = GIF


class JpegImage(File):
    """Dummy jpeg image upload object

    900 by 900 pixels.
    """

    filename = "900.jpeg"
    data = JPEG
