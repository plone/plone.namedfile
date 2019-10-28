# -*- coding: utf-8 -*-

from io import BytesIO
from logging import getLogger

import re
import xml.etree.cElementTree as et


log = getLogger(__name__)


def process_svg(data):
    content_type = None
    w = -1
    h = -1
    size = len(data)

    tag = None
    try:
        for event, el in et.iterparse(BytesIO(data), ("start",)):
            tag = el.tag
            _w = el.attrib.get("width")
            _h = el.attrib.get("height")
            if len(_w) and len(_h):
                w = int(float(re.sub(r"[^\d\.]", "", _w)))
                h = int(float(re.sub(r"[^\d\.]", "", _h)))
            break
    except et.ParseError:
        pass

    if tag == "{http://www.w3.org/2000/svg}svg" or (
        size == 1024 and b"http://www.w3.org/2000/svg" in data
    ):
        content_type = "image/svg+xml"
        w = w if isinstance(w, int) and w > 1 else 1
        h = h if isinstance(h, int) and h > 1 else 1

    return content_type, w, h
