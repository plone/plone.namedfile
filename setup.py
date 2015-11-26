from setuptools import setup, find_packages
import os

version = '2.0.10'

long_description = open("README.rst").read()
long_description += "\n"
long_description += open("CHANGES.rst").read()
long_description += "\n"
long_description += open(os.path.join("plone", "namedfile", "usage.txt")).read()

setup(name='plone.namedfile',
      version=version,
      description="File types and fields for images, files and blob files with filenames",
      long_description=long_description,
      classifiers=[
          "Framework :: Plone",
          "Framework :: Plone :: 4.2",
          "Framework :: Plone :: 4.3",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "License :: OSI Approved :: BSD License",
          ],
      keywords='plone named file image blob',
      author='Laurence Rowe, Martin Aspeli',
      author_email='plone-developers@lists.sourceforge.net',
      url='http://pypi.python.org/pypi/plone.namedfile',
      license='BSD',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['plone'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'zope.browserpage',
          'zope.component',
          'zope.security',
          'zope.traversing',
          'plone.rfc822>=1.0b2',
      ],
      extras_require = {
          'blobs': [],  # BBB
          'editor': ['plone.schemaeditor'],
          'supermodel': ['plone.supermodel'],
          'marshaler': [],  # for BBB, we now depend on this
          'scales': ['plone.scale[storage] >=1.1dev'],
          'test': ['lxml', 'plone.scale'],
      },
      )
