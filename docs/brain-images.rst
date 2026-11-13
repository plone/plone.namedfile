Brain-aware ``@@images``
========================

.. contents::
   :local:

Overview
--------

``plone.namedfile`` provides the ``@@images`` view for content objects. The same
view is also registered for catalog brains and
``plone.app.contentlisting`` objects. It exposes the same developer-facing API,
answers from the catalog's ``image_scales`` metadata first, and falls back to
the real object only when metadata cannot answer.

The metadata path does not call ``getObject()``. It is intended for listings,
search results, and other code that has a brain rather than a materialized
content object. This feature targets Plone 6.2.

Availability
------------

The brain-aware view is registered for:

* ``Products.ZCatalog.interfaces.ICatalogBrain``;
* ``plone.app.contentlisting.interfaces.IContentListingObject``, when
  ``plone.app.contentlisting`` is installed.

Get it with ``getMultiAdapter``:

.. code-block:: python

   from zope.component import getMultiAdapter

   images = getMultiAdapter((brain, request), name="images")
   tag = images.tag("image", scale="teaser")

For a contentlisting item:

.. code-block:: python

   from plone.app.contentlisting.interfaces import IContentListingObject
   from zope.component import getMultiAdapter

   item = IContentListingObject(brain)
   images = getMultiAdapter((item, request), name="images")
   html = images.srcset(
       "image",
       scale_in_src="large",
       sizes="(min-width: 768px) 50vw, 100vw",
       loading="lazy",
   )

Brains are not URL-addressable. Do not try to traverse ``@@images`` on a brain
or contentlisting wrapper; the view refuses publisher traversal. The scale URLs
it generates point at the real content object, where the bytes are served.

Public API
----------

The view provides:

``scale(fieldname=None, scale=None, height=None, width=None, mode="scale", pre=False, include_srcset=None, **parameters)``
   Return a metadata-backed scale object compatible with ``ImageScale``.

``tag(fieldname=None, scale=None, height=None, width=None, mode="scale", include_srcset=None, **kwargs)``
   Return an ``<img>`` tag.

``srcset(fieldname=None, scale_in_src="huge", sizes="", alt=<unset>, css_class=None, title=<unset>, **kwargs)``
   Return a responsive ``<img>`` tag with a width-based ``srcset``.

``picture(fieldname=None, picture_variant=None, alt=None, css_class=None, title=<unset>, lazy=True, **kwargs)``
   Return a ``<picture>`` tag for a registered picture variant.

``getImageSize(fieldname=None)``
   Return the original ``(width, height)``.

``available_sizes``
   The registry's configured scale names and dimensions.

``modified(fieldname=None)``
   The brain's modification time in milliseconds, or ``0`` when unavailable.

For ``srcset()``, an omitted ``alt`` or ``title`` defaults to the normalized
content Title. For ``picture()``, ``alt`` is emitted only when truthy.

Metadata-backed scale objects have ``data = None`` and no storage ``uid``. They
provide ``url``, ``width``, ``height``, ``mimetype``, ``filename``, ``title``,
``absolute_url()``, ``tag()``, and ``srcset_attribute()``. They never serve
bytes themselves.

Metadata-first behavior
-----------------------

The catalog stores ``brain.image_scales`` as a mapping of field names to lists
of entries. Each entry contains:

* ``filename``, ``content-type``, and ``size``;
* ``download``, the URL of the original image;
* ``width`` and ``height``;
* ``scales``: a mapping of scale name to ``download``, ``width``, and
  ``height``.

The metadata path uses those values directly. It does not read image storage and
does not wake the object. Scale URLs are built from ``download`` and the brain's
``getURL()``. Absolute (``http://``, ``https://``) and root-relative (``/...``)
downloads are used unchanged.

When the catalog has the ``image_scales`` column:

* a missing field, ``Missing.Value``, or an empty entry list means "no image";
* the view returns ``None`` or ``(0, 0)`` without waking.

When the catalog does not have the ``image_scales`` column, the view falls back
to the object-backed view for every request.

Fallback rules
--------------

Metadata is used when it can answer:

* a named scale that exists in the metadata;
* the original image when no scale or dimensions are requested;
* explicit dimensions that match a metadata scale or the original;
* the default ``"scale"`` mode;
* ``pre=True`` with metadata-answerable dimensions.

The view falls back to the real object when:

* a configured scale is missing from the metadata;
* arbitrary dimensions do not match a metadata scale;
* a non-default mode is requested;
* HiDPI is explicitly requested and configured;
* metadata is malformed, or the catalog has no ``image_scales`` column.

A scale name that is not in ``available_sizes`` returns ``None``, matching the
object-backed view. When ``getObject()`` returns ``None``, the methods return
empty results. When it raises ``Unauthorized``, the exception propagates.

``srcset()`` has one deliberate exception: a configured scale missing from the
metadata is skipped, and the rest of the ``srcset`` is rendered. A missing
selected ``scale_in_src`` still falls back.

Field resolution
----------------

An explicit ``fieldname`` is used when the field exists in the metadata.

When ``fieldname`` is omitted, the view uses the only image field. If the brain
has several image fields, the request is ambiguous: it returns ``None`` or
``(0, 0)`` and logs a debug message. Brains have no primary-field information,
so the view never calls ``getObject()`` to find one.

Some custom fields map to multiple entries. The view uses the first entry and
logs a debug message; a multi-image API is not part of this view.

Responsive ``srcset``
---------------------

``srcset()`` mirrors the object-backed view:

* it iterates the configured scales in registry order;
* it includes the original only when its width is not an available width;
* descriptors use the actual widths from the metadata;
* ``scale_in_src`` selects the ``src`` image, falling back to the first
  available width not larger than the original;
* ``sizes``, ``alt``, ``title``, ``class``, and extra attributes behave like
  the object-backed view.

Missing configured scales are skipped. The resulting ``srcset`` can therefore
be shorter than the object-backed one when metadata is incomplete.

Picture variants
----------------

``picture()`` uses the same picture variants registry as the object-backed view.
It preflights every referenced scale that has a registry width; unknown names
are skipped by the builder. If all required scales exist in the metadata, the
``<picture>`` is rendered without touching the object. If any required scale is
missing, the whole call falls back to the object.

An unknown variant logs a warning and falls back to ``tag()``, using the variant
name as a scale when it exists. A missing or empty ``sourceset`` logs a warning
and returns ``None``.

Small images commonly fall back because metadata omits scales wider than the
original image. This is expected and preserves output parity.

HiDPI
-----

Brain metadata does not contain the old-style 2x/3x scales. HiDPI is opt-in:

.. list-table::
   :header-rows: 1

   * - Call
     - HiDPI configured
     - Behavior
   * - ``include_srcset=None`` (default)
     - either
     - metadata; no HiDPI; no wake-up
   * - ``include_srcset=False``
     - either
     - metadata; no HiDPI; no wake-up
   * - ``include_srcset=True``
     - no
     - metadata; no HiDPI; no wake-up
   * - ``include_srcset=True``
     - yes
     - object-backed fallback; returns the object's HiDPI ``srcset``

``include_srcset`` is accepted by ``scale()`` and ``tag()``. It is consumed and
never rendered as an HTML attribute. ``srcset()`` and ``picture()`` do not
accept it.

Security
--------

The metadata path performs no extra permission check. It exposes the same
catalog data that search results and REST summaries already expose through
``image_scales``.

The generated scale URL resolves to the real content object. Normal ``View``
checks apply when the bytes are requested, so rendering a tag does not grant
access to the image.

Field-level read permissions are not enforced on the metadata path. The
object-backed view uses ``guarded_getattr``; the brain-aware view does not.
Protected image fields must be rendered through the object-backed view.

``Unauthorized`` from a fallback propagates. A missing or deleted object yields
empty results. Permission failures are not logged with user-identifying details.

Documented divergences
----------------------

* ``srcset()`` skips missing configured scales and can produce a shorter result.
* HiDPI is omitted by default; only an explicit ``include_srcset=True`` falls
  back to the object.
* Picture variants fall back to the object when any required scale is missing,
  which is common for small images.
* The object-backed view's no-dimension original uses the storage
  ``image-0`` URL. The metadata view uses the indexed ``image-<width>`` URL.
  Both serve the original image.
* Metadata is a catalog snapshot. A scale URL can return 404 after storage
  cleanup until the scale is regenerated.
* A request-dependent custom ``_scale_url`` override can differ from the URL
  captured at index time.
* If a contentlisting wrapper has already woken its object,
  ``getDataOrigin()`` returns the real object and the view uses the object
  path.
* Field-level permissions are not enforced on the metadata path.

Non-goals
---------

* URL traversal or serving of ``@@images`` on brains.
* Editing or uploading image fields through a brain view.
* A multi-image/relation-list API beyond the first metadata entry.
* Plone 6.1 or earlier.
* Replacing or changing ``NavigationRootScaling`` (``@@image_scale``) or
  ``cs.srcset``.

Related documentation
---------------------

``NavigationRootScaling`` (``@@image_scale``) remains available for navigation
roots and keeps its existing behavior. ``cs.srcset`` is a separate package and
is not required for this view.
