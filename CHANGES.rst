Changelog
=========

.. You should *NOT* be adding new change log entries to this file.
   You should create a file in the news directory instead.
   For helpful instructions, please see:
   https://github.com/plone/plone.releaser/blob/master/ADD-A-NEWS-ITEM.rst

.. towncrier release notes start

7.0.2 (2025-04-04)
------------------

Bug fixes:


- Adjusted schema validation to prevent file/image loading during upload/import (#167)


7.0.1 (2025-03-21)
------------------

Bug fixes:


- Work around TypeError: unhashable type: 'list' on `images-test` view.
  [maurits] (#173)


Internal:


- Update configuration files.
  [plone devs]


7.0.0 (2025-01-24)
------------------

Breaking changes:


- Drop support for Plone 5.2.  [maurits] (#4090)


Bug fixes:


- Fix DeprecationWarnings. [maurits] (#4090)


6.4.0 (2024-11-25)
------------------

New features:


- Set `Link` header with `rel="canonical"` for file downloads. @mamico (#163)


6.3.1 (2024-07-30)
------------------

Bug fixes:


- Fix: Upload a svg without width and height set  @dobri1408 (#161)


6.3.0 (2024-03-15)
------------------

New features:


- Improve contenttype detection logic for unregistered but common types.

  Change get_contenttype to support common types which are or were not registered
  with IANA, like image/webp or audio/midi.

  Note: image/webp is already a IANA registered type and also added by
  Products.MimetypesRegistry.
  [thet] (157-2)
- Support for allowed media types.

  Support to constrain files to specific media types with a "accept" attribute on
  file and image fields, just like the "accept" attribute of the HTML file input.

  Fixes: #157
  [thet] (#157)


6.2.3 (2023-11-03)
------------------

Bug fixes:


- Be more strict when checking if mimetype is allowed to be displayed inline.
  [maurits] (#1167)


6.2.2 (2023-10-18)
------------------

Bug fixes:


- Fix calculation of file modification time. @davisagli (#153)


6.2.1 (2023-09-21)
------------------

Bug fixes:


- Fix stored XSS (Cross Site Scripting) for SVG images.
  Done by forcing a download instead of displaying inline.
  See `security advisory <https://github.com/plone/plone.namedfile/security/advisories/GHSA-jj7c-jrv4-c65x>`_.
  [maurits] (#1)


6.2.0 (2023-09-14)
------------------

New features:


- Add internal modification timestamp with fallback to _p_mtime.
  [mathias.leimgruber] (#149)
- Use new internal modification timestamp as part of the hash key for scales.
  [mathias.leimgruber] (#150)


6.1.2 (2023-08-31)
------------------

Bug fixes:


- Fixed the issue where SVG images containing extensive metadata were not being displayed
  correctly (resulting in a width/height of 1px). This problem could occur when the
  <svg> tag exceeded the MAX_INFO_BYTES limit.

  Fixes `issue 147 <https://github.com/plone/plone.namedfile/issues/147>`_.
  [mliebischer] (#147)


6.1.1 (2023-06-22)
------------------

Bug fixes:


- Return a 400 Bad Request response if the `@@images` view is published without a subpath. @davisagli (#144)


Tests


- Fix tests to work with various ``beautifulsoup4`` versions.
  [maurits] (#867)


6.1.0 (2023-05-22)
------------------

New features:


- Move ``Zope2FileUploadStorable`` code from plone.app.z3cform to here to break a cyclic dependency.
  [gforcada] (#3764)


6.0.2 (2023-05-08)
------------------

Bug fixes:


- Fix picture tag when original image is used instead of a scale.
  [maurits] (#142)


6.0.1 (2023-03-14)
------------------

Tests


- Tox: explicitly test only the ``plone.namedfile`` package.  [maurits] (#50)


6.0.0 (2022-11-22)
------------------

Bug fixes:


- Log a warning when a scale for a picture variant is not found.
  Until now this gave an exception.
  [maurits] (#134)
- Prevent exception when an anonymous user is the first to load a page with a private image.
  Anonymous still gets an Unauthorized when loading the image, but that is to be expected.
  The html at least shows normally.
  Fixes `issue 135 <https://github.com/plone/plone.namedfile/issues/135>`_.
  [maurits] (#135)
- Fixed writing to the database each time an original is requested.
  This happens when requesting the original under a unique id.
  [maurits] (#3678)


6.0.0b5 (2022-10-03)
--------------------

Breaking changes:


- No longer test Plone 5.2 on 3.6 and Plone 6.0 on 3.7.
  [maurits] (#3637)


Bug fixes:


- Use ``mode`` parameter instead of deprecated ``direction`` and warn user about it.
  [petschki, maurits] (#102)


6.0.0b4 (2022-09-07)
--------------------

Bug fixes:


- Move getAllowedSizes + getQuality from CMFPlone.utils to this package.
  [jensens] (#132)


6.0.0b3 (2022-07-20)
--------------------

Bug fixes:


- Get title from ImageScale class.
  Prevents a traceback when the context is a tile.
  When no title can we found, fall back to an empty string.
  [maurits] (#128)


6.0.0b2 (2022-06-27)
--------------------

Bug fixes:


- Do not use full url in `image_scales` dictionary.
  [petschki] (#123)


6.0.0b1 (2022-06-23)
--------------------

New features:


- Creating a tag no longer generates the actual scale.
  [maurits] (#113)
- Add picture method to to ImageScaling and include it in @@image-test.
  Picture tags only work on Plone 6, with several other branches for picture variants merged.
  See `plip-image-srcsets.cfg <https://github.com/plone/buildout.coredev/blob/6.0/plips/plip-image-srcsets.cfg>`_.
  If not available (like on Plone 5.2), an ordinary image tag is created.
  [MrTango] (#113)
- Add ``@@images-test`` page for Editors.
  This shows various variants from the image field of the current context.
  It shows a list of stored scales.
  It allows purging the stored scales.
  [maurits] (#113)
- removed marking request for disable CSRF protection (need plone.scale with https://github.com/plone/plone.scale/pull/58)
  [mamico] (#177)
- use the attribute _sizes for local caching correctly available_sizes
  [mamico] (#177)
- add additional infos in scale storage only if missing
  [mamico] (#177)
- Register adapter for image fields to the new image_scales metadata.
  Use this in the image_scale view to get images from a list a brains.
  This code is not active on Plone 5, only Plone 6.
  [cekk, maurits] (#3521)


Bug fixes:


- Cleanup: isort, black, pyupgrade, remove use of six, etc.
  [maurits] (#120)


6.0.0a4 (2022-05-26)
--------------------

Bug fixes:


- Only look at the width when checking if a HiDPI image would be larger than the original.
  Otherwise HiDPI srcsets are never included when the scale is defined with a height of 65536.
  [maurits] (#114)
- Fix Unauthorized when accessing ``@@images/image`` of private image, even as Manager.
  Fixes problem introduced in previous release.
  [maurits] (#118)


6.0.0a3 (2022-02-28)
--------------------

Bug fixes:


- ``ImageScaling`` view: use ``guarded_orig_image`` to get field from a url.
  Mostly, this makes the view easier to customize.
  [maurits] (#104)


6.0.0a2 (2022-02-23)
--------------------

Breaking changes:


- Removed deprecated extras from setup.py.
  These ones are gone now: ``blobs``, ``editor``, ``marshaler``, ``scales``, ``supermodel``.
  See `issue 106 <https://github.com/plone/plone.namedfile/issues/106>`_.
  [maurits] (#106)


New features:


- Register ``AnnotationStorage`` as ``IImageScaleStorage`` multi adapter.
  Both from ``plone.scale``.
  Use this adapter in our scaling functions when we store or get an image scale.
  [maurits] (#44)


6.0.0a1 (2022-01-28)
--------------------

Breaking changes:


- Drop support for Python 2.7.
  Main target is now Plone 6, but we try to keep it running on Plone 5.2 with Python 3.
  See discussion in `plone.scale issue 44 <https://github.com/plone/plone.scale/issues/44>`_.
  [maurits] (#44)


Bug fixes:


- Fixed NameError `file` on Python 3. Use `io.IOBase` instead. (#3)


5.6.0 (2021-12-29)
------------------

New features:


- Make DefaultImageScalingFactory more flexible, with methods you can override.
  [maurits] (#104)


5.5.1 (2021-07-28)
------------------

Bug fixes:


- Cache stable image scales strongly.
  When plone.app.imaging is available, this is already done.
  Otherwise, we should do this ourselves.
  Fixes `issue 100 <https://github.com/plone/plone.namedfile/issues/100>`_.
  [maurits] (#100)


5.5.0 (2021-06-30)
------------------

New features:


- Prevent stored XSS from file upload (svg, html).
  Do this by implementing an allowlist of trusted mimetypes.
  You can turn this around by using a denylist of just svg, html and javascript.
  Do this by setting OS environment variable ``NAMEDFILE_USE_DENYLIST=1``.
  From `Products.PloneHotfix20210518 <https://plone.org/security/hotfix/20210518/reflected-xss-in-various-spots>`_.
  [maurits] (#3274)


5.4.0 (2020-06-23)
------------------

New features:


- Range support (https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests)
  [mamico] (#86)


5.3.1 (2020-04-30)
------------------

Bug fixes:


- Fix image scaling to reuse the original image when scaling is not required to allow Plone REST API to use cacheable scale URL for the original image without performance penalty [datakurre] (#92)


5.3.0 (2020-04-21)
------------------

New features:


- Change to use field value _p_mtime instead of context object _p_mtime as image scale invalidation timestamp to fix issue where context object (e.g. a document with lead image) modification invalidated all its image field scales even the images itself were not modified. [datakurre] (#91)


5.2.2 (2020-04-14)
------------------

Bug fixes:


- Close BlobFile in DefaultImageScalingFactory. [timo] (#89)
- Implement the handling of SVG files before passing it to Pillow, fixes #3063
  [sneridagh] (#3063)


5.2.1 (2019-12-11)
------------------

Bug fixes:


- Fix tiff support. Remove process_tiff and let the PIL do the work.
  [mamico] (#85)
- Fix content_type in getImageInfo when using PIL.
  [mamicp] (#85)


5.2.0 (2019-11-25)
------------------

New features:


- Load SVG files.
  [balavec] (#63)


5.1.0 (2019-10-21)
------------------

New features:


- Add new interface ``plone.namedfile.interfaces.IPluggableFileFieldValidation`` and ``plone.namedfile.interfaces.IPluggableImageFieldValidation``.
  Refactored: the fields validation now looks for adapters with this interfaces adapting field and value.
  All found adapters are called.
  The image content type checker (existed before) is by now the only adapter implemented and registered so far.
  Other adapters can be registered in related or custom code.
  [jensens] (#81)


5.0.5 (2019-10-12)
------------------

Bug fixes:


- fix ResourceWarnings for unclosed files
  [mamico] (#80)


5.0.4 (2019-06-27)
------------------

Bug fixes:


- It is now possible to customize in an easier way the ``@@images`` view [ale-rt] (#65)


5.0.3 (2019-04-29)
------------------

Bug fixes:


- Increase static MAX_INFO_BYTES to fix an issue where the filesize was not extracted properly from an image with lots of metadata. [elioschmutz] (#74)


5.0.2 (2018-11-13)
------------------

Bug fixes:


- Do not fail image upload when Exif data is bad. [maurits] (#68)


5.0.1 (2018-11-08)
------------------

Bug fixes:

- Fix a forgotten change to BytesIO.
  [pbauer]


5.0 (2018-11-02)
----------------

New features:

- Target Zope 4 (test changes only).

- Python 3 compatibility
  [pbauer, matthewwilkes, fgrcon, jensens]

Bug fixes:

- Prepare for Python 2 / 3 compatibility
  [ale-rt, pbauer, MatthewWilkes, jensens]

- remove mention of "retina" (https://github.com/plone/Products.CMFPlone/issues/2123)
  [tkimnguyen]

- Fix test to use new zope testbrowser internals.
  [davisagli]


4.2.3 (2017-09-08)
------------------

Bug fixes:

- Fix bug #56 where ``srcset`` generation failed on no given width or height if there was no sclae given.
  https://github.com/plone/plone.namedfile/pull/56
  [jensens]


4.2.2 (2017-07-03)
------------------

Bug fixes:

- Don't break DefaultImageScalingFactory, if for any reason the fieldname isn't available on the context.
  [thet]

- Different caching keys for different domains
  [mamico]


4.2.1 (2017-05-30)
------------------

Bug fixes:

- Fix #46, when ``process_png``, ``process_jpeg`` and ``process_tiff`` could fail with a ``width referenced before assignment`` error.
  [thet]

- Fix contentType attribute should be str type, what leads to validation errors (fixes `#38`_).
  [rodfersou]

- Fix bug on Image rotation if ImageIFD.XResolution or ImageIFD.YResolution are not set.
  [loechel]

- Fix: Do not log failing PIL image regognition as error, but as warning.
  [jensens]

- Fix: compatibility for Plone 4 re-added.
  [loechel]


4.2.0 (2017-03-26)
------------------

New features:

- Add retina image scales using srcset attribute.
  [didrix]


4.1.2 (2017-02-12)
------------------

Bug fixes:

- BrowserViews have no Acquisition.
  [pbauer]


4.1.1 (2017-01-20)
------------------

New features:

- Add automatic image rotation based on EXIF data for all images.
  Based on piexif library and ideas of maartenkling and ezvirtual.
  Chosen piexif as it allow read and write of exif data for future enhancements.
  http://piexif.readthedocs.org/en/latest/
  For Orientation examples and description see http://www.daveperrett.com/articles/2012/07/28/exif-orientation-handling-is-a-ghetto/ test data https://github.com/recurser/exif-orientation-examples
  Additional Test Images with different MIME-Types (JPEG and TIFF) and possible problems: https://github.com/ianare/exif-samples.git
  [loechel]

- Support SVG images
  [tomgross]


Bug fixes:

- Added handler for Tiff Images in getImageInfo.
  [loechel]

- Restructured packages.
  Moved image meta data detection in an own subfolder
  [loechel]


4.1 (2016-09-14)
----------------

New features:

- Add Pdata storage
  [vangheem]


4.0 (2016-08-12)
----------------

Incompatibilities:

- Targets Plone 5.1 only, coredev 5.0 and 4.3 are on 3.0.x branch [jensens]:

  - ``plone.supermodel``, ``plone.scale`` and ``plone.schemaeditor`` are now hard dependencies.
    The extras  in setup.py are kept for bbb reasons, but are empty.
    Conditional code is now no longer conditional.
    This simplifies the code a lot.

  - ``zope.app.file`` is no longer hard dependency.
    If it is there, its FileChunk implementation is still checked for, otherwise not.


New:

- uses adapter as factory for scales as in plone.scale>=1.5
  [jensens]

Fixes:

- Several tests were failing on Windows 10 due to binary files being opened in text mode. Fixed.
  [smcmahon]

- Prevent attempt to create a filestream_iterator from a temporary file associated with an
  uncommitted blob.
  Fixes an error on Windows 10 "WindowsError 32" by attempting to delete or access a file in use
  by another process.
  [smcmahon]

- Fix tests to work with latest plone.scale changes, where gif images are no longer converted to jpeg.
  [thet]

- Fixed test setup to use layers properly.
  [jensens]

- Fixed test isolation problem in ``test_blobfile.py``.
  [jensens]

- Fix warning on testing.zcml missing an i18n:domain.
  [gforcada]

- Fix some code analysis warnings.
  [gforcada]

3.0.8 (2016-02-26)
------------------

Fixes:

- PEP 8, UTF-8 headers, implements/adapts to decorators, doctest formatting.
  [thet, jensens]

- Workaround for method getImageSize.
  Prevent returning (-1, -1) as the size of the image.
  [andreesg]


3.0.7 (2016-02-12)
------------------

Fixes:

- Make plone.protect a soft dependency. This allows to use this package in
  setups without the Plone stack. Fixes plone/Products.CMFPlone#1311
  [thet]

3.0.6 (2016-01-08)
------------------

Fixes:

- Stabilised tests.  [gotcha]


3.0.5 (2015-11-26)
------------------

New:

- Added webdav support to image scales.
  https://github.com/plone/Products.CMFPlone/issues/1251
  [maurits]


3.0.4 (2015-10-28)
------------------

Fixes:

- No longer rely on deprecated ``bobobase_modification_time`` from
  ``Persistence.Persistent``.
  [thet]


3.0.3 (2015-08-14)
------------------

- Don't fail, when accessing the ``tag`` method of the ``@@images`` view, if
  ``scale`` returns ``None``.
  [thet]


3.0.2 (2015-03-13)
------------------

- Cache image scales using the plone.stableResource ruleset when they are
  accessed via UID-based URLs. (Requires plone.app.imaging >= 1.1.0)
  [davisagli]


3.0.1 (2014-10-23)
------------------

- Fixed inserting filename in Content-Disposition header.
  [kroman0]

- Respect field level security in download views also for primary fields.
  [jensens]

- Internationalize field factory label.
  [thomasdesvenain]


3.0.0 (2014-04-13)
------------------

- Disable CSRF protection when creating a scale so we can write to the database
  [vangheem]


2.0.5 (2014-02-19)
------------------

- Ensure zope.app.file.file module alias is created before its use in
  file package.
  [thomasdesvenain]


2.0.4 (2014-01-27)
------------------

- Disable CSRF protection when creating a scale so we can write to the database
  [vangheem]

- Validate image field : check if content is actually an image using mimetype.
  [thomasdesvenain]

- Fix: get_contenttype works when empty string is given as contentType.

- Backward compatibility of NamedFile with zope.app.file FileChunk.
  Avoids NamedFile validation unexpected failures.
  [thomasdesvenain]


2.0.5 (2014-02-19)
------------------

- Ensure zope.app.file.file module alias is created before its use in
  file package.
  [thomasdesvenain]


2.0.4 (2014-01-27)
------------------

- Backward compatibility of NamedFile with zope.app.file FileChunk.
  Avoids NamedFile validation unexpected failures.
  [thomasdesvenain]

- Validate image field : check if content is actually an image using mimetype.
  [thomasdesvenain]

- Fix: get_contenttype works when empty string is given as contentType.
  [thomasdesvenain]


2.0.3 (2013-12-07)
------------------

- Scaling Traverser now does not try to traverse two steps in one.
  This is impossible in chameleon.
  [do3cc]


2.0.2 (2013-05-23)
------------------

* Use plone.app.imaging's (>=1.0.8) quality setting if it exists.
  https://dev.plone.org/ticket/13337
  [khink]

* fix invalidation on contexts that do not implement dublin core; Notably
  portlet assignments. Fallback is bobo_modification_time. Maybe portlet
  assignments should implement modified() instead?
  [tmog]

* Fixed handling of TTW Dexterity content type image field
  data when image data is large and stored as
  zope.app.file.file.FileChunk in ZODB instead of raw string data.
  Issue appearated after Plone 4.3 migration [miohtama]


2.0.1 (2013-01-17)
------------------

* Add direction parameter support in scaling (was ignored in tag and scale
  functions).
  Now calling tag function with parameter direction='down' crops the image.
  direction='thumbnail' by default so default behaviour remains the same.
  [jriboux]

2.0 (2012-08-29)
----------------

* Move file and image value implementations here instead of extending
  the ones from zope.app.file and z3c.blobfile. This helps tame a mess
  of dependencies.
  [davisagli]

* The blob-based file and image implementations are now always available.
  (But they will only work if Zope is using a storage with blob support.)
  [davisagli]

* Add support for HEAD requests to @@images view
  [anthonygerrard]

* Add hook to override headers in subclasses of file download view
  [anthonygerrard]

* Don't set filename in header if filename contains non ascii chars.
  [do3cc]

* Adding Dexterity Image caused TypeError if jpeg file contained
  corrupt metadata. Closes http://dev.plone.org/ticket/12753.
  [patch by joka, applied by kleist]

1.0.6 - 2011-10-18
------------------

* Fix test failure.
  [davisagli]

* Fix bug in producing tag for a scale on an item with a unicode title
  [tomster]

1.0.5 - 2011-09-24
------------------

* Make the ``download`` view respect custom read permissions for the field
  being downloaded, rather than only checking the view permission for the
  object as a whole.
  [davisagli]

1.0.4 - 2011-08-21
------------------

* Fix bug in producing tag for a scale on an item whose title has non-ASCII
  characters.
  [davisagli]

* Make sure image scales of allowed attributes can be accessed on disallowed
  containers.
  [davisagli]

* Add unit tests for safe_filename, since not exercised within this module.
  (should be moved to plone.formwidget.namedfile?)
  [lentinj]

1.0.3 - 2011-05-20
------------------

* Relicense under BSD license.
  See http://plone.org/foundation/materials/foundation-resolutions/plone-framework-components-relicensing-policy
  [davisagli]

1.0.2 - 2011-05-19
------------------

* Don't omit empty string attributes from ImageScale tag.
  [elro]

1.0.1 - 2011-05-19
------------------

* In the tag method of ImageScale to allow height/width/alt/title to be
  omitted when they are supplied as a None argument.
  [elro]

* In marshalled file fields, encode the filename parameter of the
  Content-Disposition header in accordance with RFC 2231. This ensures that
  filenames with non-ASCII characters can be successfully demarshalled.
  [davisagli]

* Make the various file classes be strict about only accepting unicode
  filenames.
  [davisagli]

1.0 - 2011-04-30
----------------

* Use unique urls for accessing the original scale.
  [elro]

* Avoid Content-Disposition for image scales.
  [elro]

1.0b8 - 2011-04-12
------------------

* Declare dependency on plone.rfc822 >= 1.0b2 (for IPrimaryField).
  [davisagli]

* Add a @@display-file view which doesn't set Content-Disposition, so we don't
  force download of images, for example.
  [lentinj]

1.0b7 - 2011-03-22
------------------

* Support getting the original size as a scale.
  [elro]

* Add tag() method to scaling view.
  [elro]

* Scaling: quote values of extra tag attributes.
  [elro]

1.0b6 - 2011-02-11
------------------

* Add primary field support to @@download and @@images views.
  [elro]

* Add getAvailableSizes and getImageSize to the @@images view.
  [elro]

1.0b5 - 2010-04-19
------------------

* Add support for scaled images.  See usage.txt for details.
  [davisagli]

* Fix the field schemata so they can be used as the form schema when
  adding the field using plone.schemaeditor.
  [rossp]

1.0b4 - 2009-11-17
------------------

* Avoid using the internal _current_filename() helper, which disappeared in
  ZODB 3.9.
  [optilude]

* Add field factories for plone.schemaeditor (only installed if
  plone.schemaeditor is available)
  [davisagli]

1.0b3 - 2009-10-08
------------------

* Add plone.rfc822 field marshaler (only installed if plone.rfc822 is
  available)
  [optilude]

1.0b2 - 2009-09-17
------------------

* Add plone.supermodel import/export handlers (only installed if
  plone.supermodel is available).
  [optilude]

1.0b1 - 2009-05-30
------------------

* Make z3c.blobfile (and blobs in general) a soft dependency. You'll need to
  separately depend on z3c.blobfile (and probably pin it to version 0.1.2) to
  get the NamedBlobFile and NamedBlobImage fields. This means that
  plone.namedfile can be used with ZODB versions that do not support BLOBs.
  This policy will probably be revisited for a 2.0 release.
  [optilude]

1.0a1 - 2009-04-17
------------------

* Initial release


.. _`#38`: https://github.com/plone/plone.namedfile/issues/38
