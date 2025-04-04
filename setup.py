from setuptools import find_packages
from setuptools import setup

import os


version = "7.0.2"

description = "File types and fields for images, files and blob files with filenames"
long_description = "\n\n".join(
    [
        open("README.rst").read(),
        open("CHANGES.rst").read(),
        open(os.path.join("plone", "namedfile", "usage.rst")).read(),
    ]
)


setup(
    name="plone.namedfile",
    version=version,
    description=description,
    long_description=long_description,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Plone",
        "Framework :: Plone :: 6.0",
        "Framework :: Plone :: 6.1",
        "Framework :: Plone :: Core",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: BSD License",
    ],
    keywords="plone named file image blob",
    author="Laurence Rowe, Martin Aspeli",
    author_email="plone-developers@lists.sourceforge.net",
    url="https://pypi.org/project/plone.namedfile",
    license="BSD",
    packages=find_packages(),
    namespace_packages=["plone"],
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.9",
    install_requires=[
        "BeautifulSoup4",
        "persistent",
        "piexif",
        "Pillow",
        "plone.app.uuid>=2.2.0",
        "plone.base",
        "plone.dexterity",
        "plone.memoize",
        "plone.protect",
        "plone.rfc822>=2.0.0",
        "plone.scale[storage] >=3.0",
        "plone.schemaeditor",
        "plone.supermodel",
        "Products.CMFCore",
        "setuptools",
        "z3c.caching",
        "zope.cachedescriptors",
        "zope.copy",
        "Zope",
    ],
    extras_require={
        "test": [
            "lxml",
            "plone.app.testing",
            "plone.testing",
        ],
    },
)
