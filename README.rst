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


Brain-aware image scales
========================

Catalog brains and contentlisting objects can use the same ``@@images`` view as
content objects. The view answers from ``image_scales`` catalog metadata first
and only falls back to the real object when metadata cannot answer.

See the `brain-aware image scales documentation`_ for the API, fallback rules,
and security caveats.

.. _brain-aware image scales documentation: https://github.com/plone/plone.namedfile/blob/main/docs/brain-images.rst


Source Code
===========

 Note: This packages is licensed under a *BSD license*.
 Please do not add dependencies on GPL code!

Contributors please read the document `Process for Plone core's development <https://docs.plone.org/develop/coredev/docs/index.html>`_

Sources are at the `Plone code repository hosted at Github <https://github.com/plone/plone.namedfile>`_.
