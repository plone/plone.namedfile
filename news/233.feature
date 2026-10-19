Let WSGI servers send whole-file downloads with ``sendfile``, and iterate partial ranges in blocks.
``filestream_range_iterator`` has ``fileno`` when the response is the whole file.
``stream_data`` returns a partial range as ``partial_range_iterator``, which has no ``read``, so Zope does not hand it to ``wsgi.file_wrapper``.
Before, bjoern and pyruvate read the whole file or range in one ``read()`` call.
[mamico]
