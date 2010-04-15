from setuptools import setup, find_packages
import os

version = '1.0b5'

setup(name='plone.namedfile',
      version=version,
      description="File types tand fields for images, files and blob files with filenames",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read() + "\n" + 
                       open(os.path.join("plone", "namedfile", "usage.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='plone named file image blob',
      author='Laurence Rowe, Martin Aspeli',
      author_email='plone-developers@lists.sourceforge.net',
      url='http://pypi.python.org/pypi/plone.namedfile',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['plone'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'zope.app.file',
      ],
      extras_require = {
        'blobs':  ['z3c.blobfile'],
        'editor': ['plone.schemaeditor'],
        'supermodel': ['plone.supermodel'],
        'marshaler': ['plone.rfc822'],
        'scales': ['plone.scale[storage] >=1.1dev'],
      },
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
