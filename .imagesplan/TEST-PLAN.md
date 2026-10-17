# Test plan: brain-aware `@@images`

Status: designed, awaiting specification approval.
Covers: `scale`, `tag`, `srcset`, `picture`, `getImageSize`, `available_sizes`,
`modified`, registration, fallback, field resolution, HiDPI, and security.

## Layers and modules

- `src/plone/namedfile/testing.py`
  - Add `NamedFilePloneLayer(defaultBases=(PLONE_FIXTURE,))`.
  - Add `NAMEDFILE_PLONE_INTEGRATION` (`IntegrationTesting`) and
    `NAMEDFILE_PLONE_FUNCTIONAL` (`FunctionalTesting`).
- `src/plone/namedfile/tests/brain_images_helpers.py`
  - Shared content factories, fake brain, DOM normalizer, parity helpers,
    `getObject()` instrumentation, and patch context managers.
- `src/plone/namedfile/tests/test_brain_images.py`
  - Integration tests: registration, parity, fallback, field resolution,
    HiDPI, security contracts, zero wake-ups.
- `src/plone/namedfile/tests/test_brain_images_functional.py`
  - Browser tests: scale URLs serve the right bytes, unauthorized URL access
    is denied.

Use `IntegrationTesting` for everything except real URL serving. Do not use
`PRODUCTS_CMFPLONE_INTEGRATION_TESTING`; it pulls in robotframework. Add
`self.loadZCML(package=plone.namedfile)` only if a test needs package-local
ZCML.

## Fixtures

### Real content

```python
setRoles(portal, TEST_USER_ID, ["Manager"])
portal.invokeFactory("Image", "img1", title="Img 1")
obj = portal.img1
obj.image = NamedImage(getFile("image.png"), "image/png", "image.png")
obj.reindexObject()
brain = portal.portal_catalog(UID=obj.UID())[0]
```

- `tests/image.png` (200x200) for small-image cases: only scales up to 200px
  exist in metadata.
- `tests/900.jpg` (900x900) for `srcset` and parity cases that need larger
  scales.
- `News Item` works the same way for single-image tests.
- For multi-field content: programmatic `DexterityFTI` with two `NamedImage`
  fields (`image1`, `image2`), set both, `reindexObject()`.

### Wrappers

```python
from plone.app.contentlisting.interfaces import IContentListingObject

wrapper = IContentListingObject(brain)   # catalog wrapper
real_wrapper = IContentListingObject(obj)  # real-object wrapper
```

Use the single adapter form; `getMultiAdapter((brain, request),
IContentListingObject)` fails.

### Fake brain

Use for states real content cannot easily produce:

- malformed `image_scales`;
- multiple entries per field (relation-list shape);
- `Missing.Value` / no image;
- a `getObject()` that raises `AssertionError` or `Unauthorized`;
- a `getURL()` / `Title` / `UID` / `modified` that records access.

The fake implements `Products.ZCatalog.interfaces.ICatalogBrain`. Do not mutate
`catalog._catalog.data`.

### Stale and malformed metadata

- Clear storage after reindex: `getMultiAdapter((obj, None),
  IImageScaleStorage).clear()`; metadata remains and the URL may 404.
- Change the image and `reindexObject(update_metadata=0)` to keep old metadata.
- Shadow `brain.image_scales` for a malformed payload (`{"image": []}`,
  missing `download`, wrong types) when a fake brain is overkill.

## Zero-wake-up instrumentation

Patch `Products.ZCatalog.CatalogBrains.AbstractCatalogBrain` only:

```python
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain

def fail(*args, **kwargs):
    raise AssertionError("getObject() called on the metadata path")

with (
    patch.object(AbstractCatalogBrain, "getObject", new=fail),
    patch.object(AbstractCatalogBrain, "_unrestrictedGetObject", new=fail),
):
    html = brain_view.tag("image", scale="thumb")
```

- Strict `AssertionError` patches for fast-path tests.
- A separate counting test with a positive control: under the same patches,
  call `brain.getObject()` once and assert exactly one recorded call, proving
  the instrumentation is live.
- Install instrumentation only around the call under test. Build the
  object-backed reference view outside the patch.
- `CatalogContentListingObject.getObject()` delegates to `brain.getObject()`,
  so the same patch catches wrapper wake-ups.
- Do not patch traversal, acquisition, or `OFS` internals.

## Parity harness

Build the three views with the same request:

```python
object_view = getMultiAdapter((obj, request), name="images")
brain_view = getMultiAdapter((brain, request), name="images")
wrapper_view = getMultiAdapter((wrapper, request), name="images")
```

Compare with a DOM normalizer:

1. Parse fragments with `lxml.html.fragment_fromstring`.
2. Compare tag names and attribute dictionaries, not attribute order.
3. Assert exact URLs/UIDs when both views derive from the same indexed
   metadata. Use the `-[0-9a-f]{32}` normalization only as a fallback.
4. Compare `srcset` as ordered `(url, descriptor)` pairs.
5. For `picture`, compare every `<source>` (`srcset`, `sizes`, `media`) and the
   `<img>` (`src`, `sizes`, `width`, `height`, `title`, `alt`, `loading`,
   `class`).
6. For `scale()`, compare `url`, `width`, `height`, `mimetype`, and `.tag()`.
   Do not compare `.data`: metadata scales have `data=None` by design.
7. Restore `ImageScaling._sizes`, registry patches, HiDPI patches, and any
   monkeypatches in `tearDown`.

## Cases

### A. Registration and lookup

- Plain brain -> `BrainImageScaling`.
- `CatalogContentListingObject` -> `BrainImageScaling` with a brain origin.
- `RealContentListingObject` -> brain-aware view delegates to the object path.
- Real content object -> existing `ImageScaling`.
- The existing `images` page and `scaling.zcml` behavior are unchanged.

### B. `scale()` and `tag()`

- Named scale parity for 200px and 900px images.
- Original image when no scale/dimensions are given.
- Explicit dimensions matching a metadata scale.
- Explicit dimensions matching nothing -> fallback; result parity.
- Scale name not in `available_sizes` -> `None`.
- `mode="crop"` -> fallback.
- `pre=True` metadata-answerable path -> zero wake-ups.
- `tag()` attributes: `src`, `alt`, `title`, `width`, `height`, `class`.
- `include_srcset` is never emitted as an HTML attribute.
- Wrapper and plain-brain outputs match the object output.

### C. `srcset()`

- Exact parity for a 900px original with metadata covering all scales.
- Original included only when its width is not an available width.
- Registry order preserved.
- `scale_in_src` fallback to the first available width <= original.
- Missing scale in the bulk iteration is skipped; output is shorter and no
  fallback occurs.
- Missing selected `scale_in_src` falls back to the object.
- `sizes`, `alt`, `title`, `class`, and extra attributes match the object.
- Zero wake-ups on the in-sync path.

### D. `picture()`

- Unknown variant -> warning + metadata `tag()`.
- Full parity for a variant whose required scales all exist (patch variants and
  allowed scales consistently on both views).
- Any missing required scale -> whole-call fallback; result parity.
- `additionalScales` omitted -> all allowed except target.
- `media`, explicit `sizes`, `class="captioned"`, `loading="lazy"`, `alt`,
  `title`, `width`, `height` match the object.
- No `uuidToObject()`, `getObject()`, or `unrestrictedTraverse("@@images")` on
  the fast path.

### E. Field resolution

- Omitted fieldname + exactly one field -> that field.
- Omitted fieldname + multiple fields -> `None` / `(0, 0)` + debug log.
- Explicit fieldname present -> use it.
- Explicit fieldname absent -> `None` / `(0, 0)`.
- Multiple entries -> first entry + debug log.
- Empty entry list -> no image.
- `Missing.Value` -> no image.
- Wrapper delegates to the brain origin.

### F. Fallback matrix

- Catalog without `image_scales` column -> fallback (simulate via patch/fake).
- `Missing.Value` / no field -> no wake, empty result.
- Malformed metadata -> fallback.
- `getObject() is None` -> `None` / `(0, 0)` / `0`.
- `getObject()` raises `Unauthorized` -> propagates from every method.
- Stale metadata URL is still rendered; functional request may 404.
- Debug log on fallback; no warnings for expected fallbacks.
- `modified()` uses `brain.modified`; `getImageSize()` rules from the fallback
  ticket.

### G. HiDPI

- HiDPI configured: default and `include_srcset=False` -> no `srcset`, zero
  wake-ups.
- HiDPI configured: `include_srcset=True` -> object fallback, output matches.
- HiDPI not configured: `include_srcset=True` -> metadata only, no wake.
- `srcset()` and `picture()` are unaffected.
- `include_srcset` is consumed, not rendered.

### H. Security

- Functional: anonymous/unauthorized users cannot fetch the scale bytes from
  the generated URL.
- Fallback `Unauthorized` raises from `scale`, `tag`, `srcset`, `picture`, and
  `getImageSize`.
- Missing/deleted object yields the empty-result contract.
- Field-level permission divergence is tested and documented: metadata renders,
  object path raises.
- `RealContentListingObject` uses the object path and keeps normal enforcement.
- No user-identifying permission details in logs.

### I. Regression

- Full existing suite stays green, including the existing `test_scaling.py`,
  `test_scaling_functional.py`, and `picture.py` tests with no resolver.
- `NavigationRootScaling` tests are untouched.
- The object-backed `@@images` output is unchanged.

## Commands

```sh
# Baseline and full suite
tox -e py312-plone62

# New integration module
.tox/py312-plone62/bin/zope-testrunner \
  --test-path=src -s plone.namedfile -m 'test_brain_images'

# New functional module
.tox/py312-plone62/bin/zope-testrunner \
  --test-path=src -s plone.namedfile -m 'test_brain_images_functional'

# Existing scaling regression
.tox/py312-plone62/bin/zope-testrunner \
  --test-path=src -s plone.namedfile -m 'test_scaling$'
```

CI uses the repository's existing Plone 6.2 matrix (py310-py314). Tests must not
depend on a Python version newer than 3.10.

## Performance guard

The guard is the `getObject()`/`_unrestrictedGetObject()` call count on the
metadata path, not wall-clock timing. Do not add timing thresholds.

## Documented divergences

- `srcset()` skips missing configured scales; output can be shorter.
- HiDPI is omitted by default; `include_srcset=True` opts into an object
  fallback.
- Field-level read permissions are not enforced on the metadata path.
- Stale metadata URLs can 404 after storage cleanup; the view does not detect
  this.

## Non-goals

- URL traversal/serving on brains.
- Editing or uploading images through a brain view.
- A multi-image/relation-list API beyond the first entry.
- Plone 6.1 or earlier.
- Migrating `cs.srcset`.
