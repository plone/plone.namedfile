from pathlib import Path
from setuptools import setup


version = "8.0.0a1"

description = "File types and fields for images, files and blob files with filenames"
long_description = (
    f"{Path('README.rst').read_text()}\n"
    f"{Path('CHANGES.rst').read_text()}\n"
    f"{(Path('src') / 'plone' / 'namedfile' / 'usage.rst').read_text()}"
)

setup(
    name="plone.namedfile",
    version=version,
    description=description,
    long_description=long_description,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Plone",
        "Framework :: Plone :: 6.2",
        "Framework :: Plone :: Core",
        "Programming Language :: Python",
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
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.10",
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
        "plone.scale[storage]>=4.2.0",
        "plone.schemaeditor",
        "plone.supermodel",
        "Products.CMFCore",
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
