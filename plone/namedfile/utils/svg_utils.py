from io import BytesIO
from logging import getLogger

import re
import xml.etree.ElementTree as et


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
            w = dimension_int(el.attrib.get("width"))
            h = dimension_int(el.attrib.get("height"))
            break
    except et.ParseError:
        pass

    if tag == "{http://www.w3.org/2000/svg}svg" or (
        size == 1024 and b"http://www.w3.org/2000/svg" in data
    ):
        content_type = "image/svg+xml"
        w = w if w > 1 else 1
        h = h if h > 1 else 1

    return content_type, w, h


def dimension_int(dimension):
    if isinstance(dimension, str):
        try:
            _dimension = int(float(re.sub(r"[^\d\.]", "", dimension)))
        except ValueError:
            _dimension = 0
    elif isinstance(dimension, int):
        _dimension = dimension
    elif isinstance(dimension, float):
        _dimension = int(dimension)
    else:
        _dimension = 0

    return _dimension
