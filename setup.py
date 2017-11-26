# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup
import os


version = '4.2.4'
description = 'File types and fields for images, files and blob files with ' \
              'filenames'
long_description = ('\n\n'.join([
    open('README.rst').read(),
    open('CHANGES.rst').read(),
    open(os.path.join("plone", "namedfile", "usage.rst")).read(),
]))


setup(
    name='plone.namedfile',
    version=version,
    description=description,
    long_description=long_description,
    classifiers=[
        "Framework :: Plone",
        "Framework :: Plone :: 5.1",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: BSD License",
    ],
    keywords='plone named file image blob',
    author='Laurence Rowe, Martin Aspeli',
    author_email='plone-developers@lists.sourceforge.net',
    url='https://pypi.python.org/pypi/plone.namedfile',
    license='BSD',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['plone'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'plone.rfc822>=1.0b2',
        'plone.scale[storage] >=1.4.999',
        'plone.schemaeditor',
        'plone.supermodel',
        'setuptools',
        'zope.browserpage',
        'zope.component',
        'zope.copy',
        'zope.security',
        'zope.traversing',
        'piexif',
    ],
    extras_require={
        'test': [
            'lxml',
            'Pillow',
            'plone.testing[z2]',
        ],
        # BBB - remove in version 5
        'blobs': [],
        'editor': [],
        'marshaler': [],
        'scales': [],
        'supermodel': [],
    },
)
