from setuptools import setup, find_packages
import os

version = '2.0.5'

setup(name='plone.namedfile',
      version=version,
      description="File types and fields for images, files and blob files with filenames",
      long_description=open("README.rst").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read() + "\n" +
                       open(os.path.join("plone", "namedfile", "usage.txt")).read(),
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
          'setuptools',
          'zope.browserpage',
          'zope.component',
          'zope.security',
          'zope.traversing',
          'plone.rfc822>=1.0b2',
      ],
      extras_require = {
        'blobs':  [], # BBB
        'editor': ['plone.schemaeditor'],
        'supermodel': ['plone.supermodel'],
        'marshaler': [], # for BBB, we now depend on this
        'scales': ['plone.scale[storage] >=1.1dev'],
        'test': ['lxml', 'plone.scale'],
      },
      )
