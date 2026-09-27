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

When Pillow can encode AVIF (Pillow 11.2 or later), every image offers AVIF
twins of its scales:

* ``@@images/<field>/<scale>.avif`` serves the named scale as AVIF.
  ``scale(fieldname, "<scale>.avif")`` does the same in code.
  The scale is generated on first request and stored like any other.
* Picture tags (``@@images/picture`` and picture variants in rich text) get an
  ``image/avif`` ``<source>`` in front of each ``<source>``.
* ``tag()`` returns a ``<picture>`` with an AVIF ``<source>`` around the
  ``<img>``, also for tags built from catalog metadata.

SVG images get no twin.
An uploaded AVIF image is never used as its own scale: its plain scales and
the ``<img>`` of ``tag()`` are JPEG (PNG with alpha), so browsers without AVIF
support fall back to them.
Set the environment variable ``NAMEDFILE_AVIF=0`` to stop offering AVIF in
the markup.


Source Code
===========

 Note: This packages is licensed under a *BSD license*.
 Please do not add dependencies on GPL code!

Contributors please read the document `Process for Plone core's development <https://docs.plone.org/develop/coredev/docs/index.html>`_

Sources are at the `Plone code repository hosted at Github <https://github.com/plone/plone.namedfile>`_.
