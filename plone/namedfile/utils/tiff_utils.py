# -*- coding: utf-8 -*-

from logging import getLogger
from StringIO import StringIO

import struct

log = getLogger(__name__)


def process_tiff(data):
    """handle Tiff Images
    --> Doc http://partners.adobe.com/public/developer/en/tiff/TIFF6.pdf

    """
    content_type = 'image/tiff'
    w = -1
    h = -1
    # check for '42' as flag for tiff:
    # TODO: implement correct Image Length and Image Width lookup --> Page 14ff
    # Page 18: Tags:
    # ImageLength: Tag: 257 (101.H) Short or Long
    # ImageWidth: Tag: 256 (100.H) Short or Long

    try:
        # Image File Header (Page 13-14):
        # First 2 Bytes: Determ Byte Order
        # --> II (4949.H) --> little-endian
        # --> MM (4D4D.H) --> big-endian
        # next 2 Bytes always Number: 42
        if data[:2] == 'MM' and struct.unpack('>I', data[2:4])[0] == 42:
            endian = '>'  # big-endian encoding for the whole data stream
            log.info("Tiff Image in big-endian encoding")
        elif data[:2] == 'II' and struct.unpack('<I', data[2:4])[0] == 42:
            endian = '<'  # little-endian encoding for the whole data stream
            log.info("Tiff Image in little-endian encoding")
        else:
            # not a tiff image
            pass
        tiff = StringIO(data)
        tiff.read(4)  # Magic Header, could be skipped, already processed
        offset = struct.unpack_from(endian + 'I', tiff)  # first IFD offset
        b = tiff.read(offset)
        # Process Image File Directory
        while (b and ord(b) != 0xDA):
            field_tag = struct.unpack_from(endian + 'I', tiff)
            field_type = struct.unpack_from(endian + 'I', tiff)
            field_type = _translate_field_type(field_type)
            field_value = struct.unpack_from(endian + field_type, tiff)
            if field_tag == '256':  # ImageWidth
                w = field_value
            elif field_tag == '257':  # ImageLength
                h = field_value
                # as fields has to appear in ascending order
                # we could skip all other fields
                break
            next_offset = struct.unpack_from(endian + 'I', tiff)
            b.read(next_offset)
        width = int(w)
        height = int(h)
    except struct.error:
        pass
    except ValueError:
        pass
    except TypeError:
        pass
    return content_type, width, height


def _translate_field_type(field_type):
    if field_type == 1:
        field_type = 'I'  # BYTE: 8-bit unsigned Integer
    elif field_type == 2:
        field_type = 'c'  # 'b' 'B'
        # ASCII: 8-bit byte that contains a 7-bit ASCII code
    elif field_type == 3:
        field_type = 'H'  # SHORT: 16-bit (2-byte) unsigned integer
    elif field_type == 4:
        field_type = 'L'  # LONG: 32-bit (4-byte) unsigned integer
    elif field_type == '5':
        field_type = ''
        # RATIONAL, two LONGs: the first represents the numerator
        # of a fraction; the second, the donominator
    else:
        log.error('Unallowed field type found')