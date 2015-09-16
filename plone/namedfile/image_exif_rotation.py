from StringIO import StringIO
import PIL.Image
import exifread as exif


FLIP_LEFT_RIGHT = 0
FLIP_TOP_BOTTOM = 1
ROTATE_90 = 2
ROTATE_180 = 3
ROTATE_270 = 4
TRANSPOSE_MAP = {
    FLIP_LEFT_RIGHT: (u'Flip around vertical axis'),
    FLIP_TOP_BOTTOM: (u'Flip around horizontal axis'),
    ROTATE_270: (u'Rotate 90 clockwise'),
    ROTATE_180: (u'Rotate 180'),
    ROTATE_90: (u'Rotate 90 counterclockwise'),

}
AUTO_ROTATE_MAP = {
    0: None,
    90: ROTATE_270,
    180: ROTATE_180,
    270: ROTATE_90,
}
MIRROR_ROTATE_MAP = {
    0: None,
    90: ROTATE_270,
    180: ROTATE_180,
    270: ROTATE_90,
}

ROTATION = {'Horizontal (normal)': 1,
            'Mirrored horizontal': 2,
            'Rotated 180': 3,
            'Mirrored vertical': 4,
            'Mirrored horizontal then rotated 90 CCW': 5,
            'Rotated 90 CW': 6,
            'Mirrored horizontal then rotated 90 CW': 7,
            'Rotated 90 CCW': 8}


def exif_rotation(obj, event):
    if obj.portal_type == 'Image':
        if obj.image:

            mirror, rotation = get_exif_orientation(obj)
            transform = None
            if rotation:
                transform = AUTO_ROTATE_MAP.get(rotation, None)
                if transform is not None:
                    transform_image(obj, transform)


def get_exif(obj):
    exif_data = exif.process_file(StringIO(obj.image.data), debug=False)
    # remove some unwanted elements like thumbnails
    for key in ('JPEGThumbnail', 'TIFFThumbnail', 'MakerNote JPEGThumbnail'):
        if key in exif_data:
            del exif_data[key]
    return exif_data


def get_exif_orientation(obj):
    """Get the rotation and mirror orientation from the EXIF data

    Some cameras are storing the informations about rotation and mirror in
    the exif data. It can be used for autorotation.
    """
    exif = get_exif(obj)

    mirror = 0
    rotation = 0
    code = exif.get('Image Orientation', None)

    if code is None:
        return (mirror, rotation)

    try:
        code = int(code)
    except AttributeError:
        code = ROTATION[str(code)]
    except ValueError:
        code = ROTATION[code]

    if code in (2, 4, 5, 7):
        mirror = 1
    if code in (1, 2):
        rotation = 0
    elif code in (3, 4):
        rotation = 180
    elif code in (5, 6):
        rotation = 90
    elif code in (7, 8):
        rotation = 270

    return (mirror, rotation)


def transform_image(obj, method, REQUEST=None):
    """
    Transform an Image:
        FLIP_LEFT_RIGHT
        FLIP_TOP_BOTTOM
        ROTATE_90 (rotate counterclockwise)
        ROTATE_180
        ROTATE_270 (rotate clockwise)
    """

    image = obj.image.data
    image2 = StringIO()

    if image is not None:
        method = int(method)

        img = PIL.Image.open(StringIO(obj.image.data))
        del image
        fmt = img.format
        img = img.transpose(method)
        img.save(image2, fmt, quality=88)

        obj.image._setData(image2.getvalue())
