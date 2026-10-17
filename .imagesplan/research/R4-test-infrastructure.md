# R4 - Test infrastructure and zero-wake-up instrumentation

Status: research complete
Date: 2026-10-17
Scope: read-only investigation. No package code, tickets, MAP.md, or GitHub
state was changed.

Empirical probes were run against a local Plone 6.2.1 stack (Python 3.13.2,
`plone.app.testing` 8.0.1, `plone.app.contenttypes` 5.0.1,
`plone.app.contentlisting` 4.0.0, `plone.scale` 5.0.0). The workspace source
(`plone.namedfile` 8.1.2.dev0) was put first on `PYTHONPATH`, shadowing the
installed `plone.namedfile` 8.1.0. This is a convenience baseline, not a
project-owned tox environment.

Labels used below: **Verified** = executed in a probe; **Read** = established
from source; **Inferred** = reasonable conclusion not executed.

---

## 1. Test layers and fixtures

### Existing plone.namedfile layers

`src/plone/namedfile/testing.py:8-34` defines:

- `NamedFileTestLayer`: bases `plone.testing.zope.STARTUP` and
  `publisher.PUBLISHER_DIRECTIVES`; loads `testing.zcml`.
- `PLONE_NAMEDFILE_INTEGRATION_TESTING`
- `PLONE_NAMEDFILE_FUNCTIONAL_TESTING`

These layers have **no Plone site, no portal_catalog, and no content types**.
They are correct for the current scaling tests, but they cannot produce a
catalog brain or `image_scales` metadata. Do not use them for the brain-aware
tests.

`tests/test_scaling.py` uses the integration layer with `DummyContent`
(`SimpleItem`, `IImageScaleTraversable`, a manually registered
`IPrimaryFieldInfo`) and `MockNamedImage` (`tests/__init__.py:8-20`).
`tests/test_scaling_functional.py` uses the functional layer plus
`plone.testing.zope.Browser` and commits before browser requests
(`test_scaling_functional.py:43-69`). Both remain useful as object-backed
regression tests.

### Plone layer for brain tests

Use a package-local `PloneSandboxLayer` based on `PLONE_FIXTURE`:

```python
from plone.app.testing import (
    FunctionalTesting,
    IntegrationTesting,
    PLONE_FIXTURE,
    PloneSandboxLayer,
)


class NamedFilePloneLayer(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)


NAMEDFILE_PLONE_FIXTURE = NamedFilePloneLayer()

NAMEDFILE_PLONE_INTEGRATION = IntegrationTesting(
    bases=(NAMEDFILE_PLONE_FIXTURE,),
    name="plone.namedfile:PloneIntegration",
)
NAMEDFILE_PLONE_FUNCTIONAL = FunctionalTesting(
    bases=(NAMEDFILE_PLONE_FIXTURE,),
    name="plone.namedfile:PloneFunctional",
)
```

Why this works in Plone 6.2:

- `PloneFixture` creates `/plone` and applies
  `plone.app.contenttypes:default` and `plonetheme.barceloneta:default`
  (`plone.app.testing/layers.py:73-74`). That profile provides `Image`,
  `News Item`, and the Dexterity/namedfile setup.
- `plone.app.contenttypes` includes `plone.namedfile` in its ZCML
  (`plone/app/contenttypes/configure.zcml:35`), so the existing `@@images`
  page is registered without extra loading.
- `plone.app.contenttypes` registers the `image_scales` catalog column
  (`Products/CMFPlone/profiles/default/catalog.xml:227`; the metadata
  indexer is in `Products/CMFPlone/image_scales/indexer.py:9-22`).
- `plone.app.testing` itself requires `plone.app.contenttypes`
  (`plone.app.testing` metadata, 8.0.1), and the package's test extra already
  requires `plone.app.testing` (`setup.py:60-66`). No new test dependency is
  needed for this layer.

Do not use `Products.CMFPlone.testing.PRODUCTS_CMFPLONE_INTEGRATION_TESTING`
as the default choice: `Products/CMFPlone/testing.py` imports
`plone.app.robotframework` at module level, which is outside the namedfile
test extra. It also adds a test folder and mock mailhost that these tests do
not need.

Layer choice:

- **IntegrationTesting** for zero-wake-up assertions, catalog/brain access,
  wrapper tests, and brain-vs-object HTML comparison.
- **FunctionalTesting** only for browser/URL serving checks (scale URL returns
  the right bytes and content type). A browser GET of `@@images/...`
  traverses to the real object by design; it cannot prove the metadata path is
  wake-up free.

If a test needs package-local ZCML or a custom browser layer, add
`self.loadZCML(package=plone.namedfile)` in `setUpZope`; it is not required for
the basic layer above (probe verified `@@images` resolves through
`plone.app.contenttypes`).

---

## 2. Creating content, reindexing, and obtaining a brain

Verified recipe:

```python
from plone.app.testing import setRoles, TEST_USER_ID
from plone.namedfile.file import NamedImage
from plone.namedfile.tests import getFile

setRoles(portal, TEST_USER_ID, ["Manager"])

portal.invokeFactory("Image", "img1", title="Img 1")
obj = portal.img1
obj.image = NamedImage(getFile("image.png"), "image/png", "image.png")

# Explicit reindex is deterministic and updates catalog metadata.
obj.reindexObject()

brain = portal.portal_catalog(UID=obj.UID())[0]
```

Notes:

- `News Item` also has an `image` field and works the same way.
- `portal.portal_catalog(UID=...)` worked with the test user in the `Manager`
  role. `unrestrictedSearchResults(UID=...)` avoids permission differences;
  `plone.api.content.find(UID=...)` is equivalent (used by cs.srcset tests).
- Assigning the image and then calling `reindexObject()` is safer than relying
  on `invokeFactory(..., image=...)` to index the final value. The upstream
  CMFPlone test relies on creation indexing, but explicit reindexing removes
  ambiguity.
- `reindexObject()` calls the metadata indexer. `reindexObject(update_metadata=0)`
  intentionally leaves `image_scales` stale (see below).

### Verified metadata shape

For a 200x200 PNG (`tests/image.png`), `brain.image_scales` was a
`persistent.mapping.PersistentMapping`:

```python
{
    "image": [
        {
            "filename": "image.png",
            "content-type": "image/png",
            "size": <int>,
            "download": "@@images/image-200-<32-hex>.png",
            "width": 200,
            "height": 200,
            "scales": {
                "icon":    {"download": "@@images/image-32-<hash>.png",  "width": 32,  "height": 32},
                "listing": {"download": "@@images/image-16-<hash>.png",  "width": 16,  "height": 16},
                "mini":    {"download": "@@images/image-200-<hash>.png", "width": 200, "height": 200},
                "thumb":   {"download": "@@images/image-128-<hash>.png", "width": 128, "height": 128},
                "tile":    {"download": "@@images/image-64-<hash>.png",  "width": 64,  "height": 64},
            },
        }
    ]
}
```

The field keys and the relative `download` values come from
`src/plone/namedfile/adapters.py:36-136` (the `ImageFieldScales` adapter). The
list-per-field shape is documented in the same file at lines 62-67 and is used
by `NavigationRootScaling._tag_from_brain_image_scales`
(`src/plone/namedfile/scaling.py:944-956`).

Scale names present depend on the original width. `image.png` is 200x200, so
only scales up to width 200 are present. Use `tests/900.jpg` (900x900) when a
test needs `large`, `larger`, `great`, `huge`, etc.

### Multiple image fields

Use a small programmatic Dexterity type with two `NamedImage` fields, following
`Products/CMFPlone/image_scales/tests/test_image_scales_metadata.py:134-154`:
create a `DexterityFTI` with a model file or model source, register it on
`portal.portal_types`, `invokeFactory` the type, set both fields, then
`reindexObject()`. Verified upstream expectation: `brain.image_scales` has one
key per field (`image1`, `image2`). This test does not require
`plone.app.contenttypes` beyond what `PLONE_FIXTURE` already provides.

Relation-list fields produce a list with more than one entry per field. The
default `NavigationRootScaling` metadata path only uses the first entry
(`scaling.py:950-955`). For R4, treat relation lists as a D9/R2 case: either
build a custom FTI/field adapter or use a fake brain with a hand-built
`image_scales` payload. They are not covered by the stock `Image` type.

### Missing, malformed, stale, and cleared metadata

Missing / empty image (Verified):

```python
portal.invokeFactory("News Item", "news1", title="News 1")
news = portal.news1
news.reindexObject()
brain = portal.portal_catalog(UID=news.UID())[0]

from Missing import Value as MissingValue
assert getattr(brain, "image_scales", None) is MissingValue
assert bool(getattr(brain, "image_scales", None)) is False
```

This matches upstream
`Products/CMFPlone/image_scales/tests/test_image_scales_metadata.py:121-126`.
`Missing.Value` is falsey, so `if not getattr(brain, "image_scales", None)`
returns early without waking.

Clear scales after metadata was written (Verified):

```python
from plone.scale.storage import IImageScaleStorage
from zope.component import getMultiAdapter

storage = getMultiAdapter((obj, None), IImageScaleStorage)
storage.clear()
```

Result in the probe:

- `brain.image_scales` still contains the old `download` URL (stale metadata).
- `NavigationRootScaling.tag(brain, "image", scale="thumb")` still rendered the
  stale URL.
- Resolving that stale UID through the object-backed `@@images` view raised
  `zope.publisher.interfaces.NotFound`.
- Calling the object-backed `scale()` again regenerated the scale under the
  same UID; a later `obj.reindexObject()` restored equivalent metadata.

This is the core stale-metadata fixture for D8: metadata can answer, but the
scale URL may 404 until something regenerates the storage entry.

Stale metadata without clearing (Verified):

```python
obj.image = NamedImage(getFile("900.jpg"), "image/jpeg", "900.jpg")
obj.reindexObject(update_metadata=0)  # indexes but does not update metadata
# brain.image_scales still has the old 200x200/image.png entry
```

The probe confirmed the old `download` value was unchanged. This simulates an
object changed without a metadata refresh. Use it to assert the view either
falls back or accepts the stale URL, per the R2/D8 decision.

Malformed metadata (Verified for one technique):

```python
# The catalog returns an Acquisition wrapper around the generated brain.
# Assigning here shadows the metadata for this brain instance.
brain.image_scales = {"image": []}
```

The assignment succeeded in the probe. This is convenient for tests that only
need a malformed payload. If this proves brittle across ZCatalog versions, use
a small `FakeBrain` implementing `Products.ZCatalog.interfaces.ICatalogBrain`
with `image_scales`, `getURL()`, `Title`, `UID`, `modified`, and optionally
`getObject()` raising `AssertionError`. Do **not** try to mutate
`catalog._catalog.data[rid]` directly: in the probe it was a tuple and raised
`AttributeError`.

Clearing scales through the UI (`@@images-clear`) requires a POST and the
`cmf.ModifyPortalContent` permission. Tests should use the
`IImageScaleStorage.clear()` adapter directly.

---

## 3. Instrumenting `getObject()` without breaking acquisition

The catalog returns an `Acquisition.ImplicitAcquisitionWrapper` around a
dynamically generated brain class. `getObject` and `_unrestrictedGetObject`
are inherited from `Products.ZCatalog.CatalogBrains.AbstractCatalogBrain`
(`CatalogBrains.py:28-86`). Patching the base class methods preserves
acquisition because the original method still receives the acquisition-wrapped
`self` and still calls `aq_parent`/`restrictedTraverse`/`unrestrictedTraverse`
exactly as before.

Strict zero-wake assertion:

```python
from unittest.mock import patch
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain


def fail(*args, **kwargs):
    raise AssertionError("getObject() called on the metadata path")


with (
    patch.object(AbstractCatalogBrain, "getObject", new=fail),
    patch.object(AbstractCatalogBrain, "_unrestrictedGetObject", new=fail),
):
    html = view.tag("image", scale="thumb")
```

Counting form (better diagnostics):

```python
calls = []
orig_get = AbstractCatalogBrain.getObject
orig_unrestricted = AbstractCatalogBrain._unrestrictedGetObject


def counting_get(brain, *args, **kwargs):
    calls.append(("getObject", brain.getPath()))
    return orig_get(brain, *args, **kwargs)


def counting_unrestricted(brain, *args, **kwargs):
    calls.append(("_unrestrictedGetObject", brain.getPath()))
    return orig_unrestricted(brain, *args, **kwargs)


with (
    patch.object(AbstractCatalogBrain, "getObject", new=counting_get),
    patch.object(
        AbstractCatalogBrain, "_unrestrictedGetObject", new=counting_unrestricted
    ),
):
    html = view.tag("image", scale="thumb")

assert calls == []
```

Add a **positive control** in a separate test: under the same patch, call
`brain.getObject()` once and assert exactly one recorded call. Without this, a
zero-call assertion can pass because the patch target was never exercised.
Verified: `brain.getObject()` produced `[("/plone/img1")]` with the counting
wrapper.

Important details:

- Patch only `Products.ZCatalog.CatalogBrains.AbstractCatalogBrain`, not
  `OFS` internals, `restrictedTraverse`, or acquisition. Replacing traversal
  with a mock would test the wrong thing and could break acquisition.
- `CatalogContentListingObject.getObject()` delegates to
  `self._brain.getObject()` (`plone/app/contentlisting/catalog.py:61-69`), so
  patching the brain catches wrapper wake-ups too.
- `CatalogContentListingObject.__getattr__` first looks on
  `aq_base(self._brain)` for the attribute (`catalog.py:38-50`). Therefore
  `wrapper.image_scales` reads metadata without waking. If an attribute is
  absent from the brain, `__getattr__` falls back to `getObject()`, so the
  metadata attribute must exist (it does in Plone 6.2, including
  `Missing.Value` for empty images).
- `getDataOrigin()` returns the brain without waking
  (`plone/app/contentlisting/catalog.py:53-59`). The brain-aware view should
  use it (or reject objects without a brain origin) rather than calling
  `getObject()` to find one.
- Install instrumentation only around the call under test. Building the
  object-backed reference view or calling `brain.getObject()` for a positive
  control must happen outside the strict patch.
- `brain.getURL()` and `brain.getPath()` are metadata/acquisition operations;
  they did not wake the object in the probe.

Create the contentlisting wrapper with the **single adapter**:

```python
from plone.app.contentlisting.interfaces import IContentListingObject

wrapper = IContentListingObject(brain)  # or queryAdapter(brain, IContentListingObject)
```

Do not use `getMultiAdapter((brain, request), IContentListingObject)`: it
raises `ComponentLookupError` because the registration is
`CatalogContentListingObject` for `ICatalogBrain`, and the factory takes only
the brain. (Verified.)

A functional/browser test can still assert that a scale URL serves the right
bytes; it cannot assert "the metadata path did not wake the object", because
URL traversal intentionally resolves the real object.

---

## 4. Parity harness

### View construction

```python
from plone.app.contentlisting.interfaces import IContentListingObject
from zope.component import getMultiAdapter

object_view = getMultiAdapter((obj, request), name="images")

brain_view = getMultiAdapter((brain, request), name="images")

wrapper = IContentListingObject(brain)
wrapper_view = getMultiAdapter((wrapper, request), name="images")
```

The first line works today through the existing
`IImageScaleTraversable` registration (`scaling.zcml`). The brain/wrapper
lines depend on the registration chosen in R1.

### What to compare

Use a DOM normalizer rather than raw strings. Existing tests use regex and
`doctest._ellipsis_match`, which is fine for fixed expected output but too
brittle for brain-vs-object parity.

Suggested normalization:

1. Parse fragments with `lxml.html.fragment_fromstring` (lxml is already a
   test dependency, `setup.py:60-66`) or BeautifulSoup.
2. Compare tag names and attribute dictionaries, not attribute order.
3. Normalize absolute URL host/path only if the two views use different
   contexts; in the same layer both are `http://nohost/plone/...`.
4. Normalize scale UIDs only as a fallback:
   `re.sub(r"-[0-9a-f]{32}", "-HASH", value)`.
   Prefer asserting exact UIDs when both views derive from the same catalog
   metadata. In the probe, `NavigationRootScaling.tag(brain, ...)` and the
   object-backed `@@images.tag(...)` produced the **same** UID for `thumb`.
5. For `srcset`, split on commas and compare `(normalized_url, descriptor)`
   pairs, preserving or explicitly ignoring order.
6. For `picture`, compare the `<source>` `srcset` and `<img>` `src`, `sizes`,
   `width`, `height`, `title`, `alt`, and `loading` attributes.

Method-specific caveats:

- `scale()`: compare `uid`, `url`, `width`, `height`, `mimetype`, and
  `.tag()`. Do **not** compare `.data`: metadata-backed scales come from
  `pre_scale` and have `data=None` (`plone/scale/storage.py:220-299`), while
  the object-backed view generates bytes. Data equality is a different test
  (and should use the object path).
- `tag()`: the existing object-backed `tag()` calls `scale(..., pre=True)`
  (`scaling.py:723-733`), so it is already metadata-friendly on the object
  side.
- `srcset()`: the object-backed implementation calls `pre_scale` and
  `getImageSize`; the latter needs the real image field. A metadata-only
  implementation must get original width/height from `image_scales` instead.
  Include a 900px image so scales are not truncated by the 200px original.
- `picture()`: the current implementation uses `get_picture_variants`,
  `ImageScaling._sizes`, and `uuidToObject` (patched in existing tests at
  `test_scaling.py:523-535`). For parity, patch the same variant configuration
  and allowed scales on both views, and ensure the brain path does not call
  `uuidToObject`/`getObject`. The metadata-backed picture design is D11.
- HiDPI: old-style HiDPI `2x`/`3x` data is **not** present in
  `image_scales`. `NavigationRootScaling._supports_hidpi` explicitly disables
  the metadata fast path when HiDPI is configured
  (`scaling.py:894-898, 937-939`). A parity test must either disable HiDPI or
  expect a documented fallback/wake-up. Patch
  `ImageScaling.getHighPixelDensityScales` on both views for deterministic
  tests; existing tests use this pattern.

Control knobs and cleanup:

- `ImageScaling._sizes` is a class-level cache. Set it in `setUp` and restore
  it in `tearDown` (existing tests do this at `test_scaling.py:318-329`).
- Register or monkeypatch `IAvailableSizes` and picture variants consistently
  for both views.
- Use the same `request` for both views.
- Generate the object-backed scale before or after reindex; either order
  worked in the probe because metadata was created by `pre_scale` and the
  object path found the same stored info. If a test needs to prove lazy
  generation, clear storage first and compare the resulting UID.

### Functional / browser layer

For served URLs:

```python
from plone.testing.zope import Browser
import transaction

transaction.commit()
browser = Browser(self.layer["app"])
browser.handleErrors = False
browser.addHeader("Referer", self.layer["app"].absolute_url())
browser.open(scale.url)
assert browser.headers["content-type"] == "image/png"
```

This follows `tests/test_scaling_functional.py:63-69`. Check bytes with PIL
(`assertImage`) when the scale is generated. Do not use this layer for
zero-wake-up assertions.

---

## 5. Commands and baseline

### Project commands (from `tox.ini`)

The project test command is `zope-testrunner --all --test-path={toxinidir}/src
-s plone.namedfile {posargs}` (`tox.ini:85-93`).

```bash
tox -e test                 # Plone 6.2-dev constraints, all tests
tox -e py312-plone62        # per envlist; also py310/py311/py313/py314
tox -e lint
```

Tox installs packages; it was **not** run for this read-only ticket.

### Direct command with the local 6.2 stack

The local environment used for the baseline:

```bash
cd /home/erral/dev/images/plone.namedfile
PYTHONPATH=$PWD/src \
  /home/erral/dev/collective.expired404/.venv/bin/zope-testrunner \
  --all --test-path=src -s plone.namedfile
```

Observed baseline (2026-10-17):

```text
Total: 137 tests, 0 failures, 0 errors and 1 skipped in 0.813 seconds.
```

Breakdown from the runner output: 19 unit tests, 54 functional tests,
64 integration tests. The single skip is pre-existing; it was not introduced
by this investigation.

Single-module commands (Verified):

```bash
# test_scaling.py only
PYTHONPATH=$PWD/src /home/erral/dev/collective.expired404/.venv/bin/zope-testrunner \
  --test-path=src -s plone.namedfile -m 'test_scaling$'

# test_scaling_functional.py only
PYTHONPATH=$PWD/src /home/erral/dev/collective.expired404/.venv/bin/zope-testrunner \
  --test-path=src -s plone.namedfile -m 'test_scaling_functional'
```

Results: `test_scaling.py` 70 tests when selected with `-t test_scaling`
(including the functional module's matching names); selecting the module with
`-m 'test_scaling$'` ran 54 tests, 0 failures. `test_scaling_functional.py`
ran 16 tests, 0 failures.

New tests should live in `src/plone/namedfile/tests/test_brain_images.py` (or
similar) so the existing `tests` package discovery finds them. Run just that
module with:

```bash
... --test-path=src -s plone.namedfile -m 'test_brain_images'
```

`-s` means package; do not pass a module name to `-s`. Use `-m` for a module
filter and `-t` for a test-name filter.

### Baseline caveats

- The local 6.2.1 env is not the tox-pinned `6.2-dev` constraint set, and it
  has `plone.namedfile` 8.1.0 installed while `PYTHONPATH` shadows it with the
  workspace 8.1.2.dev0. Treat the numbers as a smoke baseline, not release
  evidence.
- The `.pyenv` `6.2-py3.13` and `6.2-py3.14` environments inspected do not
  have Plone installed. `/home/erral/dev/plone.formwidget.geolocation/venv`
  is Plone 6.0.15 and must not be used for 6.2 tests.
- T1 should create/record a proper tox or uv environment and rerun the same
  commands. The suite was fast (under one second) in the local stack; a clean
  tox environment will spend most of its time installing.
- `plone.app.contenttypes` must be importable for `PLONE_FIXTURE` to apply its
  profile. It is a hard requirement of `plone.app.testing` in 6.2, but if a
  future minimal test environment drops it, the Plone layer will fail during
  setup.

---

## 6. Recommended test-plan outline for D9

1. **Regression layer**: keep the existing `NamedFileTestLayer` tests
   unchanged; run the full suite before and after the implementation.
2. **Plone integration layer**: the `NamedFilePloneLayer` above.
3. **Content fixtures**: `Image`/`News Item` with `image.png` (200x200) and
   `900.jpg` (900x900), plus an empty item.
4. **Metadata states**: populated, `Missing.Value`, cleared scales, stale via
   `reindexObject(update_metadata=0)`, and malformed (`brain.image_scales =
   {"image": []}` or a fake brain).
5. **Zero wake-up**: strict patch of `getObject` and
   `_unrestrictedGetObject`, with a positive-control test; repeat for
   `scale`, `tag`, `srcset`, `picture`, and wrapper input.
6. **Parity**: brain vs object vs `IContentListingObject` wrapper, normalized
   DOM, exact UID when possible; data comparison only on the object path.
7. **HiDPI**: configured and not configured; expect fallback/no metadata
   `srcset` when configured.
8. **Security**: reuse existing guarded-access patterns
   (`test_scaling.py:809-813`, `test_scaling_functional.py:177-192`) on brain
   and wrapper; assert no wake-up on denied paths where the metadata can
   answer.
9. **Functional**: scale URL content-type and dimensions, following
   `test_scaling_functional.py`.
10. **Commands**: full suite and the single new module command above; T1 owns
    the official environment baseline.

---

## Sources

Package source:

- `src/plone/namedfile/testing.py:8-34` - existing layers.
- `src/plone/namedfile/tests/test_scaling.py:310-329, 523-535, 809-813` -
  existing integration fixture, picture/variant patching, guarded access.
- `src/plone/namedfile/tests/test_scaling_functional.py:43-69, 177-192` -
  browser fixture and guarded access.
- `src/plone/namedfile/scaling.py:723-733, 794-883, 886-976` - object-backed
  tag/srcset, `NavigationRootScaling` metadata fast path and fallback.
- `src/plone/namedfile/adapters.py:36-136` - `image_scales` field shape,
  relative `download` values, `pre_scale` use.
- `src/plone/namedfile/scaling.zcml` - existing `@@images` registration.
- `setup.py:60-66` - test extras (`lxml`, `plone.app.testing`,
  `plone.testing`).
- `tox.ini:85-93, 149-160` - test runner command and `test` environment.

Installed Plone 6.2.1 stack (read-only):

- `plone/app/testing/layers.py:32-74, 190-214` - `PloneFixture`, profiles,
  site creation.
- `plone/app/testing/helpers.py:267-312` - `PloneSandboxLayer`.
- `Products/CMFPlone/image_scales/indexer.py:9-22` - metadata indexer.
- `Products/CMFPlone/image_scales/adapters.py:13-33` - per-field adapter.
- `Products/CMFPlone/image_scales/tests/test_image_scales_metadata.py:121-154`
  - missing metadata, populated metadata, multiple image fields.
- `Products/CMFPlone/profiles/default/catalog.xml:227` - `image_scales`
  column.
- `Products/ZCatalog/CatalogBrains.py:28-86` - `getObject`,
  `_unrestrictedGetObject`.
- `plone/app/contentlisting/catalog.py:16-69` - wrapper delegation,
  `getDataOrigin`, `getObject`.
- `plone/scale/storage.py:220-320, 385` - `pre_scale`, `scale`,
  `get_or_generate`, `clear`.
- `plone/app/contenttypes/configure.zcml:35` - includes
  `plone.namedfile`.
