Introduction
============

This package contains fields and wrapper objects for storing:

* A file with a filename
* An image with a filename

Blob-based and non-blob-based types are provided. The blob-based types
require the ZODB3 package to be at version 3.8.1 or later,
and BLOBs to be configured in zope.conf.

plone.supermodel handlers are registered.

See the `image handling section of Plone documentation <https://6.docs.plone.org/classic-ui/images.html#all-image-scales-in-the-srcset>`_ to learn how to
use the features provided by this package.


AVIF image scales
=================

AVIF images are about half the size of JPEG images of the same visual quality,
but need a browser that supports the format.
The imaging control panel (registry record ``plone.avif_mode``, from
``plone.base``) chooses how image scales use it:

``avif_with_fallback`` (the default)
  Plain scales keep their format, except that an uploaded AVIF image gets
  JPEG scales (PNG with alpha): the plain scales are the fallback.
  Picture tags (``@@images/picture``, ``ImageScaling.picture()`` and picture
  variants in rich text) get an ``image/avif`` ``<source>`` in front of each
  ``<source>``: browsers that can show AVIF load it, the others load the JPEG
  or PNG scale.
  ``@@images/<field>/<scale>.avif`` serves the AVIF version of a named scale,
  ``scale(fieldname, "<scale>.avif")`` does the same in code.
  ``tag()`` is untouched: a plain ``<img>`` with the usual scale.
  In the ``image_scales`` catalog metadata each scale carries the stable URL
  of its AVIF version as ``avif.download``, next to the plain ``download``,
  so listings, plone.restapi and Volto can offer it without waking the object.

``avif_only``
  Every scale is encoded as AVIF, including the ``<img>`` of ``tag()``, its
  high pixel density ``srcset`` and the ``image_scales`` catalog metadata.
  Fewer scales to store, but browsers without AVIF support show broken images.

``disabled``
  No conversion: scales keep the format of the uploaded image.
  An uploaded JPEG gets JPEG scales, an uploaded AVIF gets AVIF scales and
  is served as uploaded. ``<scale>.avif`` scale names are not found.

AVIF scales are generated on demand and stored like any other scale.
They are encoded with the control panel's AVIF quality (default 65, which looks
like JPEG 85-90 at about half the size) and encoding speed (default 8).
SVG images are never encoded as AVIF.
Without AVIF support in Pillow (11.2 or later, built with libavif) the mode is
``disabled``.


Source Code
===========

 Note: This packages is licensed under a *BSD license*.
 Please do not add dependencies on GPL code!

Contributors please read the document `Process for Plone core's development <https://docs.plone.org/develop/coredev/docs/index.html>`_

Sources are at the `Plone code repository hosted at Github <https://github.com/plone/plone.namedfile>`_.
