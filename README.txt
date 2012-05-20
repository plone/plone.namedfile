Introduction
============

This package contains fields and wrapper objects for storing:

  * A file with a filename
  * An image with a filename
 
Blob-based and non-blob-based types are provided. The blob-based types
require the ZODB3 package to be at version 3.8.1 or later,
and BLOBs to be configured in zope.conf.
    
plone.supermodel handlers are registered if plone.supermodel is installed.
The [supermodel] extra will ensure this.
  
See the usage.txt doctest for more details.

Note: This packages is licensed under a BSD license. Contributors, please do
not add dependencies on GPL code.
