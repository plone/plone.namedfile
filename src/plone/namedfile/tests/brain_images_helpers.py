"""Shared fixtures and assertions for brain-aware image scale tests."""

from DateTime import DateTime
from lxml import html as lxml_html
from Missing import Value as MissingValue
from plone.app.contentlisting.interfaces import IContentListingObject
from plone.dexterity.content import Item
from plone.dexterity.fti import DexterityFTI
from plone.namedfile import field as namedfile
from plone.namedfile.file import NamedImage
from plone.namedfile.tests import getFile
from plone.scale.storage import IImageScaleStorage
from plone.supermodel import model
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from Products.ZCatalog.interfaces import ICatalogBrain
from unittest.mock import patch
from zope.component import getMultiAdapter
from zope.component import getSiteManager
from zope.component.factory import Factory
from zope.component.interfaces import IFactory
from zope.interface import implementer

import contextlib
import uuid


class IMultiImage(model.Schema):
    image1 = namedfile.NamedImage(title="Image 1", required=False)
    image2 = namedfile.NamedImage(title="Image 2", required=False)


def _unique_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _set_image(
    obj,
    fieldname="image",
    source="image.png",
    filename=None,
    content_type="image/png",
):
    filename = filename or source
    setattr(
        obj,
        fieldname,
        NamedImage(getFile(source), content_type, filename),
    )


def create_image(
    portal,
    id=None,
    filename="image.png",
    content_type="image/png",
    title="Image",
):
    """Create a cataloged Image object with one named image field."""
    id = id or _unique_id("img")
    portal.invokeFactory("Image", id, title=title)
    obj = portal[id]
    _set_image(obj, source=filename, content_type=content_type)
    obj.reindexObject()
    return obj


def create_large_image(portal, id=None, title="Large Image"):
    """Create a cataloged 900x900 JPEG Image object."""
    return create_image(
        portal,
        id=id,
        filename="900.jpg",
        content_type="image/jpeg",
        title=title,
    )


def get_brain(portal, obj, unrestricted=False):
    """Return the catalog brain for obj."""
    catalog = portal.portal_catalog
    if unrestricted:
        return catalog.unrestrictedSearchResults(UID=obj.UID())[0]
    return catalog(UID=obj.UID())[0]


def wrapper_for(brain):
    """Wrap a brain in the contentlisting adapter."""
    return IContentListingObject(brain)


def first_image_entry(brain, fieldname="image"):
    """Return the first metadata entry for a field."""
    return brain.image_scales[fieldname][0]


def create_multi_image_type(portal, type_name=None):
    """Register a two-image Dexterity type and return its type name."""
    type_name = type_name or _unique_id("MultiImage")
    fti = DexterityFTI(type_name)
    fti.schema = "plone.namedfile.tests.brain_images_helpers.IMultiImage"
    fti.klass = "plone.dexterity.content.Item"
    portal.portal_types._setObject(type_name, fti)

    sm = getSiteManager()
    if sm.queryUtility(IFactory, name=type_name) is None:
        sm.registerUtility(Factory(Item, title=type_name), IFactory, name=type_name)
    return type_name


def create_multi_image_item(portal, type_name, id=None):
    """Create and catalog an item of the two-image test type."""
    id = id or _unique_id("multi")
    portal.invokeFactory(type_name, id, title="Multi")
    obj = portal[id]
    _set_image(obj, fieldname="image1", filename="image1.png")
    _set_image(obj, fieldname="image2", filename="image2.png")
    obj.reindexObject()
    return obj


def clear_scales(obj):
    """Remove stored scales while leaving the catalog metadata intact."""
    storage = getMultiAdapter((obj, None), IImageScaleStorage)
    storage.clear()


def make_metadata_stale(obj, filename="900.jpg", content_type="image/jpeg"):
    """Change the image and reindex without refreshing image_scales metadata."""
    _set_image(obj, source=filename, content_type=content_type)
    obj.reindexObject(update_metadata=0)
    return obj


@contextlib.contextmanager
def shadow_image_scales(brain, value):
    """Temporarily replace a brain's image_scales metadata."""
    old = brain.image_scales
    brain.image_scales = value
    try:
        yield brain
    finally:
        brain.image_scales = old


def scale_entry(download, width, height):
    return {"download": download, "width": width, "height": height}


def image_entry(
    filename="image.png",
    content_type="image/png",
    size=100,
    download="@@images/image-200-deadbeef.png",
    width=200,
    height=200,
    scales=None,
):
    return {
        "filename": filename,
        "content-type": content_type,
        "size": size,
        "download": download,
        "width": width,
        "height": height,
        "scales": scales if scales is not None else {},
    }


def empty_image_scales():
    return {"image": []}


def malformed_image_scales():
    return {"image": [image_entry(download=None)]}


def multi_entry_image_scales():
    entry = image_entry()
    return {"image": [entry, dict(entry)]}


@implementer(ICatalogBrain)
class FakeBrain:
    """A minimal catalog brain for malformed/edge-case tests.

    getObject() raises by default so metadata tests fail loudly if they wake.
    Pass ``get_object`` to opt into a fallback result.
    """

    def __init__(
        self,
        image_scales=MissingValue,
        url="http://nohost/plone/fake",
        title="Fake",
        uid="fake-uid",
        modified=None,
        get_object=None,
        path="/plone/fake",
    ):
        self.image_scales = image_scales
        self._url = url
        self._title = title
        self._uid = uid
        self._modified = modified if modified is not None else DateTime(2026, 1, 1)
        self._get_object = get_object
        self._path = path
        self.accessed = set()

    def __repr__(self):
        return f"<FakeBrain {self._path}>"

    @property
    def Title(self):
        self.accessed.add("Title")
        return self._title

    @Title.setter
    def Title(self, value):
        self._title = value

    @property
    def UID(self):
        self.accessed.add("UID")
        return self._uid

    @UID.setter
    def UID(self, value):
        self._uid = value

    @property
    def modified(self):
        self.accessed.add("modified")
        return self._modified

    @modified.setter
    def modified(self, value):
        self._modified = value

    def getPath(self):
        self.accessed.add("getPath")
        return self._path

    def getURL(self, relative=0):
        self.accessed.add("getURL")
        return self._url

    def _unrestrictedGetObject(self):
        self.accessed.add("_unrestrictedGetObject")
        if self._get_object is None:
            raise AssertionError("getObject() called on a metadata-only FakeBrain")
        return self._get_object()

    def getObject(self, REQUEST=None):
        self.accessed.add("getObject")
        return self._unrestrictedGetObject()

    def getRID(self):
        return 0

    def has_key(self, key):
        return False

    def __contains__(self, name):
        return False


@contextlib.contextmanager
def instrument_get_object(strict=False):
    """Record AbstractCatalogBrain.getObject wake-ups.

    ``strict=True`` raises before delegating, which is the fast-path
    assertion. ``strict=False`` records and delegates, which is the positive
    control.
    """
    calls = []
    original_get = AbstractCatalogBrain.getObject
    original_unrestricted = AbstractCatalogBrain._unrestrictedGetObject

    def _record(kind, brain):
        try:
            path = brain.getPath()
        except Exception:
            path = "<unknown>"
        calls.append((kind, path))

    def get_object(brain, *args, **kwargs):
        _record("getObject", brain)
        if strict:
            raise AssertionError(f"getObject() called on the metadata path: {brain!r}")
        return original_get(brain, *args, **kwargs)

    def unrestricted_get_object(brain, *args, **kwargs):
        _record("_unrestrictedGetObject", brain)
        if strict:
            raise AssertionError(
                f"_unrestrictedGetObject() called on the metadata path: {brain!r}"
            )
        return original_unrestricted(brain, *args, **kwargs)

    with (
        patch.object(AbstractCatalogBrain, "getObject", new=get_object),
        patch.object(
            AbstractCatalogBrain,
            "_unrestrictedGetObject",
            new=unrestricted_get_object,
        ),
    ):
        yield calls


def counting_get_object_calls():
    return instrument_get_object(strict=False)


def strict_get_object_calls():
    return instrument_get_object(strict=True)


def _parse_srcset(value):
    result = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.rsplit(None, 1)
        if len(bits) == 2:
            result.append(tuple(bits))
        else:
            result.append((part, ""))
    return tuple(result)


def _normalize_attr(name, value):
    if name == "srcset":
        return _parse_srcset(value)
    if name == "class":
        return tuple(sorted(value.split()))
    return value


def _element_signature(element):
    attrs = tuple(
        sorted(
            (name, _normalize_attr(name, value))
            for name, value in element.attrib.items()
        )
    )
    children = tuple(_element_signature(child) for child in element)
    return (element.tag, attrs, children)


def assert_html_equal(testcase, actual, expected):
    """Compare HTML fragments without depending on attribute order."""
    actual_root = lxml_html.fragment_fromstring(actual, create_parent="div")
    expected_root = lxml_html.fragment_fromstring(expected, create_parent="div")
    testcase.assertEqual(
        len(actual_root),
        len(expected_root),
        f"Different top-level node count: {actual!r} != {expected!r}",
    )
    for actual_node, expected_node in zip(actual_root, expected_root):
        testcase.assertEqual(
            _element_signature(actual_node),
            _element_signature(expected_node),
            f"HTML mismatch: {actual!r} != {expected!r}",
        )


def assert_srcset_equal(testcase, actual, expected):
    testcase.assertEqual(_parse_srcset(actual), _parse_srcset(expected))


def assert_scale_equal(testcase, actual, expected, compare_tag=True):
    """Compare scale metadata; never compare file data."""
    for attribute in ("url", "width", "height", "mimetype"):
        testcase.assertEqual(
            getattr(actual, attribute),
            getattr(expected, attribute),
            f"scale {attribute} mismatch",
        )
    if compare_tag:
        testcase.assertEqual(actual.tag(), expected.tag())
