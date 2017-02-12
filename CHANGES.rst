Changelog
=========

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
  Choosen piexif as it allow read and write of exif data for future enhancements.
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

  - ``plone.supermodel``, ``plone.scale`` and ``plone.schemaeditor`` are now hard depedencies.
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
  uncommited blob.
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

- PEP 8, UTF-8 headers, implements/adapts to decorators, doctest formating.
  [thet, jensens]

- Workarround for method getImageSize.
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
  separately depend on z3c.blobfile (and probably pin it to versio 0.1.2) to
  get the NamedBlobFile and NamedBlobImage fields. This means that
  plone.namedfile can be used with ZODB versions that do not support BLOBs.
  This policy will probably be revisited for a 2.0 release.
  [optilude]

1.0a1 - 2009-04-17
------------------

* Initial release
