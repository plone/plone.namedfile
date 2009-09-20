Introduction
============

This package contains fields and wrapper objects for storing:

  * A file with a filename
  * An image with a filename
 
BLOB based types are supported if the z3c.blobfile package is installed.
This will also require the ZODB3 package to be at version 3.8.1 or later,
and BLOBs to be configured in zope.conf.

One way to make sure that z3c.blobfile is installed is to depend on the 
[blobs] extra to this package, e.g.::

    install_requires = [
        ...
        'plone.namedfile[blobs]',
    ]
    
plone.supermodel handlers are registered if plone.supermodel is installed.
The [supermodel] extra will ensure this.
  
See the usage.txt doctest for more details.
