# -*- coding: utf-8 -*-

from logging import getLogger
from StringIO import StringIO

import struct


log = getLogger(__name__)


def process_tiff(data):
    """handle Tiff Images
    --> Doc http://partners.adobe.com/public/developer/en/tiff/TIFF6.pdf

    """
    content_type = None
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
        endian = None
        if data[:2] == 'MM' and struct.unpack('>I', data[2:4])[0] == 42:
            content_type = 'image/tiff'
            endian = '>'  # big-endian encoding for the whole data stream
            log.info('Tiff Image in big-endian encoding')
        elif data[:2] == 'II' and struct.unpack('<I', data[2:4])[0] == 42:
            content_type = 'image/tiff'
            endian = '<'  # little-endian encoding for the whole data stream
            log.info('Tiff Image in little-endian encoding')
        else:
            # not a tiff image
            log.info('Endian or 42 Check failed')

        if endian:
            tiff = StringIO(data)
            tiff.read(4)  # Magic Header, could be skipped, already processed
            offset = struct.unpack_from(endian + 'I', tiff)  # first IFD offset
            b = tiff.read(offset)
            # Process Image File Directory
            while (b and ord(b) != 0xDA):
                field_tag = struct.unpack_from(endian + 'I', tiff)
                field_type = struct.unpack_from(endian + 'I', tiff)
                field_type = translate_field_type.get(field_type, field_type)
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
    except struct.error:
        pass
    except ValueError:
        pass
    except TypeError:
        pass

    width = int(w)
    height = int(h)
    return content_type, width, height


translate_field_type = {
    """handle Tiff Image File Directory Types
    --> Doc http://partners.adobe.com/public/developer/en/tiff/TIFF6.pdf
    page 14-16
    """
    # TODO: translate to correct python struct mapping
    # TODO: check mappings
    '1': 'I',  # BYTE: 8-bit unsigned Integer
    '2': 'c',  # 'b' 'B'
               # ASCII: 8-bit byte that contains a 7-bit ASCII code
    '3': 'H',  # SHORT: 16-bit (2-byte) unsigned integer
    '4': 'L',  # LONG: 32-bit (4-byte) unsigned integer
    '5': '',  # RATIONAL, two LONGs: the first represents the numerator
              # of a fraction; the second, the donominator
    '6': '',  # SBYTE: An 8-bit signed (twos-complement) integer
    '7': '',  # UNDEFINED
    '8': '',  # SSHORT: A 16-bit (2-byte) signed (twos-complement) integer
    '9': '',   # SLONG: A 32-bit (4-byte) signed (twos-complement) integer
    '10': '',  # SRATIONAL: Two SLONG's (mutator, denominator)
    '11': '',  # FLOAT: Single precision (4-byte) IEEE format.
    '12': '',  # DOUBLE: Double precision (8-byte) IEEE format.
}
