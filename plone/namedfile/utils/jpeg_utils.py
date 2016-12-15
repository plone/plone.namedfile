# -*- coding: utf-8 -*-

from logging import getLogger
from StringIO import StringIO

import struct


log = getLogger(__name__)


def process_jpeg(data):
    size = len(data)
    content_type, w, h = None, -1, -1

    if (size >= 2) and data.startswith('\377\330'):  # handle JPEGs
        content_type = 'image/jpeg'
        jpeg = StringIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            w = -1
            h = -1
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF):
                    b = jpeg.read(1)
                while (ord(b) == 0xFF):
                    b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack('>HH', jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack('>H', jpeg.read(2))[0]) - 2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except struct.error:
            pass
        except ValueError:
            pass
        except TypeError:
            pass

    return content_type, width, height
