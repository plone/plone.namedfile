from plone.namedfile.utils import safe_basename


def test_unix_style_filename():
    assert safe_basename('/farmyard/cows/daisy') == 'daisy'


def test_windows_style_filename():
    safe_basename('F:\\FARMYARD\\COWS\\DAISY.TXT') == 'DAISY.TXT'


def test_macos_style_filename():
    assert safe_basename('Macintosh Farmyard:Cows:Daisy Text File') == 'Daisy Text File'
