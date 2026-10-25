Store the missing size and image dimensions of blob files written by older versions, the first time they are read.
This writes once per file to the database, also on a GET request; ``plone.protect`` accepts this write.
The image scales are not invalidated by it.
To disable this, set the environment variable ``NAMEDFILE_BACKFILL_ON_READ=0``.
Then call ``backfill_metadata()`` on the ``NamedBlobFile`` and ``NamedBlobImage`` objects explicitly, for example in a script.
If your database is read-only for some Zope instances, for example with read-only ZEO clients or database replicas, you must disable it there, otherwise requests that read old files fail on commit.
[jensens]
