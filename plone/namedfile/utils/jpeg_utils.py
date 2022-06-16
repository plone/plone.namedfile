from io import BytesIO
from logging import getLogger

import struct


log = getLogger(__name__)


def process_jpeg(data):
    content_type = None
    w = -1
    h = -1
    size = len(data)

    if (size >= 2) and data.startswith(b"\377\330"):  # handle JPEGs
        content_type = "image/jpeg"
        jpeg = BytesIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            while b and ord(b) != 0xDA:
                while ord(b) != 0xFF:
                    b = jpeg.read(1)
                while ord(b) == 0xFF:
                    b = jpeg.read(1)
                if ord(b) >= 0xC0 and ord(b) <= 0xC3:
                    jpeg.read(3)
                    h, w = struct.unpack(">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0]) - 2)
                b = jpeg.read(1)
        except struct.error:
            pass
        except ValueError:
            pass
        except TypeError:
            pass

    width = int(w)
    height = int(h)
    return content_type, width, height
