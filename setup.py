# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup
import os


version = '3.0.9'
description = "File types and fields for images, files and blob files with filenames"  # noqa
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
        "Framework :: Plone :: 4.3",
        "Framework :: Plone :: 5.0",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
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
        'setuptools',
        'plone.rfc822>=1.0b2',
        'zope.app.file',
        'zope.browserpage',
        'zope.component',
        'zope.copy',
        'zope.security',
        'zope.traversing',
    ],
    extras_require={
        'editor': ['plone.schemaeditor'],
        'scales': ['plone.scale[storage] >=1.1'],
        'supermodel': ['plone.supermodel'],
        'test': [
            'lxml',
            'Pillow',
            'plone.namedfile[supermodel, scales]',
            'Zope2',
        ],
        # BBB
        'blobs': [],
        'marshaler': [],
    },
)
