from setuptools import find_packages
from setuptools import setup

import os


version = "6.0.0b3"

description = "File types and fields for images, files and blob files with " "filenames"
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
        "Framework :: Plone :: 5.2",
        "Framework :: Plone :: 6.0",
        "Framework :: Plone :: Core",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
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
    install_requires=[
        "persistent",
        "piexif",
        "plone.app.uuid",
        "plone.rfc822>=2.0.0",
        "plone.scale[storage] >=3.0",
        "plone.schemaeditor",
        "plone.supermodel",
        "setuptools",
        "zope.browserpage",
        "zope.cachedescriptors",
        "zope.component",
        "zope.copy",
        "zope.security",
        "zope.traversing",
    ],
    extras_require={
        "test": [
            "plone.app.testing",
            "lxml",
            "Pillow",
            "plone.testing[z2]",
        ],
    },
)
