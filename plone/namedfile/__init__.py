from plone.namedfile.file import NamedFile, NamedImage
from plone.namedfile.file import NamedBlobFile, NamedBlobImage

# BBB alias for zope.app.file.file.FileChunk
try:
	import zope.app.file
except ImportError:
	import sys
	sys.modules['zope.app.file'] = sys.modules['plone.namedfile']
