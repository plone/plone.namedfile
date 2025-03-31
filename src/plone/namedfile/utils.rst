Utility functions
=================

safe_basename
-------------

::

    >>> from plone.namedfile.utils import safe_basename

Used in the widget itself to strip off any path, regardless of platform::

    >>> safe_basename('/farmyard/cows/daisy')
    'daisy'

    >>> safe_basename('F:\FARMYARD\COWS\DAISY.TXT')
    'DAISY.TXT'

    >>> safe_basename('Macintosh Farmyard:Cows:Daisy Text File')
    'Daisy Text File'
