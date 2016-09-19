# -*- coding: utf-8 -*-

from logging import getLogger

import struct


log = getLogger(__name__)


def process_png(data):
    content_type, w, h = None, -1, -1
    size = len(data)
    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    if (
        (size >= 24) and data.startswith('\211PNG\r\n\032\n') and
        (data[12:16] == 'IHDR')
    ):
        content_type = 'image/png'
        w, h = struct.unpack('>LL', data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack('>LL', data[8:16])
        width = int(w)
        height = int(h)

    return content_type, width, height
