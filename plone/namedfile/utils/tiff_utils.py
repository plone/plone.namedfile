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
            if field_type == 1:
                field_type = 'I'  # BYTE: 8-bit unsigned Integer
            elif field_type == 2:
                field_type = 'c' # 'b' 'B'
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
            field_value = struct.unpack_from(endian + field_type, tiff)
            if field_tag == '256':  # ImageWidth
                w = field_value
            next_offset = struct.unpack_from(endian + 'I', tiff)
            b.read(next_offset)

            while (ord(b) != 0xFF):
                b = tiff.read(1)
            while (ord(b) == 0xFF):
                b = tiff.read(1)
            if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                tiff.read(3)
                h, w = struct.unpack('>HH', tiff.read(4))
                break
            else:
                jpeg.read(int(struct.unpack('>H', jpeg.read(2))[0]) - 2)
            b = jpeg.read(1)
        width = int(w)
        height = int(h)

            offset = struct.unpack('>HH', data[4:8])[0]
            while offset < size and (w == -1 or h == -1):
                tag, typ, count, value = struct.unpack(">HHL4s", data[offset: offset + 12])
                tag = struct.unpack('>H', data[offset:offset + 2])[0]
                stype = struct.unpack('>H', data[offset + 2:offset + 4])[0]
                value = struct.unpack('>HH', data[offset + 4:offset + 8])[0]
                new_offset = struct.unpack('>HH', data[offset + 8:offset + 12])[0]
                if tag == 256:  # tag 256: ImageWidth (100.H) Short or Long
                    w = value
                elif tag == 257:  # tag 257: ImageLength (101.H) Short or Long
                    h = value
                log.info("Found Tag: %s at Offset: %s; Type: %s; Value: %s; new Offset: %s",
                         tag, offset, stype, value, new_offset)
                offset = offset + new_offset
        elif data[:2] == 'II' and struct.unpack('<H', data[2:4])[0] == 42:
            fd = ImageFileDirectory_v2(prefix='MM')
            # litle-endian
            offset = struct.unpack('<HH', data[4:8])[0]
            while offset < size and (w == -1 or h == -1):
                tag, typ, count, value = struct.unpack("<HHL4s", data[offset: offset + 12])
                tag = struct.unpack('<H', data[offset:offset + 2])[0]
                stype = struct.unpack('<H', data[offset + 2:offset + 4])[0]
                value = struct.unpack('<HH', data[offset + 4:offset + 8])[0]
                new_offset = struct.unpack('<HH', data[offset + 8:offset + 12])[0]
                if tag == 256:  # tag 256: ImageWidth (100.H) Short or Long
                    w = value
                elif tag == 257:  # tag 257: ImageLength (101.H) Short or Long
                    h = value
                log.info("Found Tag: %s at Offset: %s; Type: %s; Value: %s; new Offset: %s",
                         tag, offset, stype, value, new_offset)
                offset = offset + new_offset
        else:
            # not a tiff image
            pass
        width = int(w)
        height = int(h)
    except struct.error:
        pass
    except ValueError:
        pass
    except TypeError:
        pass
