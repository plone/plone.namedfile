# -*- coding: utf-8 -*-
import struct


def process_webp(data):
    """extract the width and height from a webp image"""
    content_type = None
    w = -1
    h = -1
    size = len(data)
    # See WebP spec (https://developers.google.com/speed/webp/docs/riff_container)
    # And VP8 Data Format and Decoding Guide (RFC 6386) https://datatracker.ietf.org/doc/html/rfc6386
    # The first 4 bytes are the RIFF chunk size
    # The next 4 bytes are the RIFF chunk type
    # The next 4 bytes are the VP8 chunk type
    # The next 4 bytes are the VP8 chunk size
    if (size >= 24) and data.startswith(b"RIFF") and (data[12:16] == b"VP8X"):
        content_type = "image/webp"
        w, h = struct.unpack(">LL", data[16:24])
    elif (
        (size >= 24) and data.startswith(b"RIFF") and (data[12:16] == b"VP8 ")
    ):
        content_type = "image/webp"
        w, h = struct.unpack(">LL", data[16:24])

    return content_type, w, h
