from setuptools import setup, find_packages
import os

version = '3.0.4.dev0'

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
          "Programming Language :: Python",
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
          'exifreader',
          'setuptools',
          'zope.browserpage',
          'zope.component',
          'zope.security',
          'zope.traversing',
          'plone.rfc822>=1.0b2',
      ],
      extras_require={
          'blobs': [],  # BBB
          'editor': ['plone.schemaeditor'],
          'supermodel': ['plone.supermodel'],
          'marshaler': [],  # for BBB, we now depend on this
          'scales': ['plone.scale[storage] >=1.1'],
          'test': ['lxml', 'plone.scale'],
      },
      )
