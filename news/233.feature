Add ``fileno`` to ``filestream_range_iterator`` when the response is the whole file.
WSGI servers like bjoern and pyruvate then send the blob with ``sendfile`` instead of reading it into memory in one ``read()`` call.
Range requests still use ``read``, because these servers ignore the range when they send the file descriptor.
[mamico]
