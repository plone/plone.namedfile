Convert scales to the format chosen in the imaging control panel (``plone.scale_format``: JPEG, WebP or AVIF).
The format is part of the scale parameters only when it is set, so the urls of scales stay the same until it is.
Scales that are not generated yet now get the extension of the format they will have.
Needs the ``format`` option of ``plone.scale.scale.scaleImage``.
@jladage
