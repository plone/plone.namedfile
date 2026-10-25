Add ``backfill_metadata()`` to ``NamedBlobFile`` and ``NamedBlobImage``.
It stores the size and, for images, the dimensions of objects written by older versions.
It may read the whole blob, so the caller decides when to run it.
[jensens]
