# R1 — Brain view registration and resolution

Status: closed. Scope: registration and lookup only. No package code, MAP.md or
other tickets were changed.

## Verdict

Register **two named `images` pages**, both pointing at the same brain-aware
view class:

1. `Products.ZCatalog.interfaces.ICatalogBrain` (plain catalog brains).
2. `plone.app.contentlisting.interfaces.IContentListingObject` (contentlisting
   wrappers), guarded with
   `zcml:condition="installed plone.app.contentlisting"` because that package is
   not a dependency of `plone.namedfile`.

Both can coexist with the existing
`for="plone.namedfile.interfaces.IImageScaleTraversable"` page. A plain brain
matches only the `ICatalogBrain` page; a contentlisting wrapper matches only the
`IContentListingObject` page. Registering only for `ICatalogBrain` does **not**
make wrappers resolve, and registering only for `IContentListingObject` does
**not** make plain brains resolve.

`getMultiAdapter` does not check the page permission. The permission and
`allowed_attributes` matter for traversal/ZPT security, so keep
`permission="zope2.View"` and list all public methods.

## 1. Can a second `images` page coexist?

Yes.

- `browser:page` registers an adapter keyed by `(for_, layer)`, `name`, and
  `IBrowserRequest`. The ZCML discriminator includes the `for` interface:
  `discriminator=('view', (for_, layer), name, IBrowserRequest)` in
  `zope.browserpage/metaconfigure.py` (`page()`), upstream:
  <https://github.com/zopefoundation/zope.browserpage/blob/6.0/src/zope/browserpage/metaconfigure.py#L187>.
  Plone 6.2 pins `zope.browserpage==6.0`.
- The object-backed page is registered for
  `.interfaces.IImageScaleTraversable` at
  `src/plone/namedfile/scaling.zcml:12-18`. `IImageScaleTraversable` is a plain
  marker interface (`src/plone/namedfile/interfaces.py:47-50`).
- `Products.ZCatalog` brains implement only `ICatalogBrain`, not the namedfile
  marker: `@implementer(ICatalogBrain)` on `AbstractCatalogBrain` in
  `Products/ZCatalog/CatalogBrains.py:27-28`, and the interface at
  `Products/ZCatalog/interfaces.py:253`.
- Because the `for` interfaces are disjoint, only one page is found for each
  context. `plone.app.event` (`images` for `IOccurrence`),
  `plone.app.tiles` (`images` for `IPersistentTile`) and `plone.app.imaging`
  (`images` for Archetypes `IBaseObject`) already demonstrate multiple
  coexisting `images` pages for different `for` interfaces.

Which one wins:

| Context | Provided interface | Matching registration | Result |
|---|---|---|---|
| Plain catalog brain | `ICatalogBrain` | `ICatalogBrain` page | Brain-aware view |
| `CatalogContentListingObject` | `IContentListingObject` | `IContentListingObject` page | Brain-aware view; origin is the brain |
| `RealContentListingObject` | `IContentListingObject` | `IContentListingObject` page | Brain-aware view; origin is a real object, so delegate to the object-backed view |
| Dexterity/content object | `IImageScaleTraversable` | Existing page | Existing `ImageScaling` |
| Object with none of these | — | none | `ComponentLookupError` (unless an add-on registers `for="*"`) |

There is no `images` page `for="*"` in Plone core. A `for="*"` registration is
the least specific and loses to any of the three specific registrations above.

## 2. Contentlisting wrappers

`CatalogContentListingObject` is declared with
`@implementer(IContentListingObject)` and is the adapter from
`ICatalogBrain`:

- `src/plone/app/contentlisting/catalog.py:15` (`@implementer(...)`).
- `src/plone/app/contentlisting/configure.zcml:37-40` (adapter from
  `Products.ZCatalog.interfaces.ICatalogBrain`).

Sources are from tag `4.0.0`, the version pinned by Plone 6.2
(`plone.app.contentlisting==4.0.0` in
<https://dist.plone.org/release/6.2-dev/constraints.txt#L164>). Master is
identical to this tag for `catalog.py`, `realobject.py`, `interfaces.py` and
`configure.zcml`.

### `__getattr__` behaviour

`CatalogContentListingObject.__getattr__` does:

1. `getattr(aq_base(self._brain), name, missing)` — metadata lookup on the
   brain first.
2. Only if that misses, `getattr(aq_base(self.getObject()), name, missing)` —
   this **wakes the object**.

Evidence: `catalog.py:38-51`.

Consequences:

- `getattr(wrapper, "image_scales")` is metadata-only **if** the catalog has the
  `image_scales` column. If the column is absent, the same `getattr` falls
  through to `getObject()` and wakes the object.
- `Title` is metadata-only only if the brain has `Title`; otherwise it wakes.
- `getObject()` caches the real object in `_cached_realobject`
  (`catalog.py:61-70`).

### Is `getDataOrigin()` the right way to reach the brain?

Yes for `CatalogContentListingObject`, with one caveat:

```python
def getDataOrigin(self):
    if self._cached_realobject is not None:
        return self._cached_realobject
    return self._brain
```

Evidence: `catalog.py:53-59`.

- Before anything calls `getObject()`, `getDataOrigin()` returns the brain
  without waking it.
- After something has called `getObject()`, `getDataOrigin()` returns the
  already-woken real object. The view must therefore **check the origin type**
  (`ICatalogBrain.providedBy(origin)`) rather than assume it is a brain.
- `RealContentListingObject.getDataOrigin()` always returns its real object
  (`realobject.py:47-54`). This matters because `IContentListingObject` is
  provided by both wrapper classes, so registering for that interface also
  matches real-object wrappers.

Recommended metadata-path branch:

```python
origin = context.getDataOrigin() if IContentListingObject.providedBy(context) else context
if ICatalogBrain.providedBy(origin):
    # metadata path; origin.image_scales, origin.Title, origin.getURL()
else:
    # real object or real-object wrapper: delegate to the object-backed @@images
```

Do **not** call `context.getObject()` to decide; that is the waking call.

## 3. `allowed_attributes`, layer and permission

The existing page uses:

```xml
<browser:page
    name="images"
    for=".interfaces.IImageScaleTraversable"
    class=".scaling.ImageScaling"
    allowed_attributes="scale tag"
    permission="zope2.View"
    />
```

`src/plone/namedfile/scaling.zcml:12-18`.

Facts:

- `permission` is a required argument of the `browser:page` directive
  (`metaconfigure.py:117`). Plone's object-backed page uses `zope2.View`.
- `allowed_attributes` only populates the view's security checker
  (`required[name] = permission` then `defineChecker(new_class,
  Checker(required))`): `metaconfigure.py:171-184`, especially
  `_handle_allowed_attributes` at `metaconfigure.py:441-447`.
- Programmatic `getMultiAdapter` is a component-registry lookup. It does not run
  the checker; the checker is used when the view is accessed through Zope's
  security machinery (publisher traversal / guarded attribute access). The
  adapter registration itself is at `metaconfigure.py:186-190`.
- No browser layer is required. The directive defaults to
  `IDefaultBrowserLayer` (`metaconfigure.py:119`), which is what the existing
  page uses. `zope.publisher.browser.TestRequest` provides
  `IDefaultBrowserLayer` by default, so tests do not need a custom layer.
- `allowed_attributes` also feeds the generated view's
  `_simple__whitelist` (`metaconfigure.py:180-182`), used by the generic
  `simple.publishTraverse`. If the brain view defines its own
  `publishTraverse`, that is independent; if it does not, only the allowed
  names are traversable.

Recommended value for the new page:

```xml
allowed_attributes="scale tag srcset picture getImageSize available_sizes modified"
```

This is a superset of the existing page and exposes the full method surface.
`zope2.View` is correct: listing images must be renderable for anonymous
visitors. The permission does not prevent trusted Python code or a test from
calling `getMultiAdapter`.

## 4. Prior art

### `NavigationRootScaling` (`@@image_scale`)

`src/plone/namedfile/scaling.py:886-985`; registered at
`src/plone/namedfile/scaling.zcml:33-39`.

- It is registered for `plone.base.interfaces.INavigationRoot`, **not** for
  brains. It takes the brain as an explicit argument: `tag(self, brain,
  fieldname, **kwargs)` (`scaling.py:909`).
- `_supports_image_scales_metadata` checks whether `image_scales` is in the
  catalog schema (`scaling.py:887-892`).
- `_tag_from_brain_image_scales` reads
  `brain.image_scales[fieldname][0]["scales"][scale]`
  (`scaling.py:949-956`), uses `download`, `height`, `width`, and joins
  `brain.getURL()` with `download` unless `download` is already absolute
  (`scaling.py:969-975`).
- It handles `brain.Title` being callable, explicitly because the argument may
  be a `CatalogContentListingObject` (`scaling.py:961-965`).
- It falls back to `brain.getObject()` and the object-backed `@@images`
  (`scaling.py:909-917`). That fallback is explicitly **not** wanted on the
  metadata path of the new view.
- It disables old-style HiDPI output when the site has 2x/3x scales
  (`scaling.py:894-897`, `937-938`), because metadata does not carry it.

This is the closest existing code for the metadata shape, but it is not a
registration precedent for `@@images` on brains.

### `cs.srcset` (`@@image_helper`)

`/home/erral/dev/images/cs.srcset/src/cs/srcset/configure.zcml:19-24` registers
`image_helper` for `"*"`, not for brains. The helper takes the item as an
argument (`helper.py:6-30`) and does `hasattr(item, "image_scales")`, then
`item.getObject()` on fallback (`helper.py:32-38`). It treats the item as a
brain, contentlisting object or real object because the view is context-free.
It has no brain-specific registration and does not use `getDataOrigin()`.

### Plone REST API and Volto

- `DefaultJSONSummarySerializer` adapts the context to
  `IContentListingObject` and reads catalog metadata; it blocklists
  `getDataOrigin`, `getObject` and `getUserData` from serialized summaries
  (`src/plone/restapi/serializer/summary.py:57-62`, `73-100`).
- Block serialization gets a brain from `catalog.searchResults(...)[0]` and reads
  `getattr(brain, "image_scales", None)` directly
  (`src/plone/restapi/serializer/blocks.py:80-94`, `273-288`).
- Volto's `Image` component uses `item.image_scales` when present, otherwise the
  real object's image field (`packages/volto/src/components/theme/Image/Image.jsx`:
  `isFromRealObject = !item.image_scales`, line 39). It does not call
  `getObject()`.

## 5. Conflicts and gotchas

1. **Same `(for, layer, name)` conflicts at ZCML time.** A new page with exactly
   the same `for`, default layer and `name="images"` from another package
   produces a configuration conflict; it is not a silent override. Different
   `for` interfaces coexist (the discriminator includes `for`). Overrides require
   `includeOverrides`, not a second plain registration.
2. **`IContentListingObject` also covers `RealContentListingObject`.** The
   adapter for `Products.CMFCore.interfaces.IContentish` is registered in the
   same `configure.zcml:42-45`. The view must handle both a brain origin and a
   real-object origin.
3. **`getDataOrigin()` can return an already-woken object.** `CatalogContentListingObject`
   caches `_cached_realobject`; after any `getObject()` call the origin is no
   longer the brain (`catalog.py:53-70`). Check `ICatalogBrain.providedBy`.
4. **Generic `getattr` on a catalog wrapper is not metadata-safe.** It tries the
   brain first and only then wakes the object (`catalog.py:38-51`). Use
   `getDataOrigin()` and an explicit brain check for metadata.
5. **`plone.app.contentlisting` is not a dependency.** `plone.namedfile` 8.1.1
   requires `Products.CMFCore`, which requires `Products.ZCatalog`; it does not
   require `plone.app.contentlisting` (PyPI metadata for `plone.namedfile`
   8.1.1 and `Products.CMFCore` 3.9). The `IContentListingObject` registration
   must be conditional. `zcml:condition="installed ..."` is an import check, not
   an include-order check:
   `zope.configuration/xmlconfig.py:398-413`.
6. **Keep the brain module import-safe.** If the brain view module imports
   `plone.app.contentlisting` at the top, the `ICatalogBrain` registration alone
   will fail in an environment without contentlisting. Use a separate module
   with a guarded import, or lazy import inside the wrapper branch.
7. **`image_scales` can be `Missing.Value`.** Non-image content can have
   `brain.image_scales == Missing.Value` (CMFPlone's own test asserts this).
   `Missing.Value` is falsy (`Missing/__init__.py:__bool__`), so a truthiness
   guard handles it, but do not assume it is `None` or a dict.
8. **Metadata has no HiDPI 2x/3x scales.** The `scales` dict contains only
   `download`, `width`, `height` per named scale (`adapters.py:112-116`). The
   `NavigationRootScaling` docs say old-style HiDPI is not available
   (`scaling.py:934-938`). Do not synthesize HiDPI on the metadata path.
9. **Brains are not annotatable.** Do not route the brain view through
   `IImageScaleStorage`/`AnnotationStorage`; that is for real objects
   (`scaling.zcml:44-51` registers the storage adapter for `* *`).
10. **`ImageScale` needs a `data` object.** `ImageScale.__init__` does
    `self.data = getattr(self.context, self.fieldname)` when no data is supplied
    and then reads `self.data.contentType`
    (`scaling.py:94-109`). Passing a brain directly would wake it. A brain-backed
    scale object must build its URL from metadata `download` instead.
11. **`Title` shape differs.** A plain brain's `Title` is a metadata value; a
    `CatalogContentListingObject.Title` is a method (and its `Title` attribute
    is callable). `NavigationRootScaling` already normalizes this
    (`scaling.py:961-965`).
12. **`for="*"` is safe but lowest priority.** No core package registers
    `images` for `*`; the three existing core `images` pages target
    `IOccurrence`, `IPersistentTile` and Archetypes `IBaseObject`. A future
    add-on `for="*"` page would lose to these specific registrations.
13. **Plone 6.2 pins Zope 6.2, not Zope 5.** The 6.2-dev constraints pin
    `Zope==6.2`, `Products.ZCatalog==7.4`, `zope.browserpage==6.0`,
    `zope.configuration==7.1`, `plone.app.contentlisting==4.0.0`. The
    `browser:page` mechanics above are the Zope 6.2 mechanics.

## 6. Recommended ZCML

`Products.ZCatalog` is a transitive dependency of `Products.CMFCore`, so the
`ICatalogBrain` registration can be unconditional. `plone.app.contentlisting` is
not a dependency and must be conditional.

```xml
<!-- Plain catalog brains. -->
<browser:page
    name="images"
    for="Products.ZCatalog.interfaces.ICatalogBrain"
    class=".brain_scaling.BrainImageScaling"
    allowed_attributes="scale tag srcset picture getImageSize available_sizes modified"
    permission="zope2.View"
    />

<!-- Contentlisting wrappers (plone.app.contentlisting is optional). -->
<configure zcml:condition="installed plone.app.contentlisting">
  <browser:page
      name="images"
      for="plone.app.contentlisting.interfaces.IContentListingObject"
      class=".brain_scaling.BrainImageScaling"
      allowed_attributes="scale tag srcset picture getImageSize available_sizes modified"
      permission="zope2.View"
      />
</configure>
```

`scaling.zcml` already declares the `browser` and `zcml` namespaces
(`scaling.zcml:1-5`). The class should live in a new module (for example
`src/plone/namedfile/brain_scaling.py`) with a guarded
`plone.app.contentlisting` import so the unconditional brain registration does
not import that optional package.

## 7. Proof strategy

For the view ticket, a minimal integration test can use a stub brain. The test
layer's request provides `IDefaultBrowserLayer`; `getMultiAdapter` is the
lookup under test.

```python
from DateTime import DateTime
from Products.ZCatalog.interfaces import ICatalogBrain
from zope.component import getMultiAdapter
from zope.interface import implementer


@implementer(ICatalogBrain)
class FakeBrain:
    UID = "brain-uid"
    modified = DateTime("2026-01-01T00:00:00Z")
    Title = "News item"
    image_scales = {
        "image": [
            {
                "filename": "image.jpg",
                "content-type": "image/jpeg",
                "size": 1234,
                "download": "@@images/image-400-abc.jpg",
                "width": 800,
                "height": 600,
                "scales": {
                    "preview": {
                        "download": "@@images/image-400-abc.jpg",
                        "width": 400,
                        "height": 300,
                    },
                },
            }
        ]
    }

    def getURL(self, relative=False):
        return "http://nohost/plone/news"

    def getObject(self, REQUEST=None):
        raise AssertionError("brain view must not wake the object")


def test_brain_images_view_resolves_without_waking(self):
    request = self.layer["request"]
    view = getMultiAdapter((FakeBrain(), request), name="images")
    self.assertTrue(view.tag("image", scale="preview").startswith("<img"))
    # Any call to getObject() above would have raised AssertionError.
```

For the contentlisting wrapper, use a real Plone/contentlisting test layer (so
the `IContentListingObject` adapter from brain is registered) or instantiate
`CatalogContentListingObject(FakeBrain())` directly. The important assertion is:

```python
wrapper = CatalogContentListingObject(FakeBrain())
view = getMultiAdapter((wrapper, self.layer["request"]), name="images")
self.assertTrue(view.tag("image", scale="preview").startswith("<img"))
# FakeBrain.getObject() must not be called.
```

Also add a resolution-order regression test:

```python
from plone.namedfile.scaling import ImageScaling
from plone.namedfile.brain_scaling import BrainImageScaling

self.assertIsInstance(
    getMultiAdapter((FakeBrain(), request), name="images"), BrainImageScaling
)
self.assertIsInstance(
    getMultiAdapter((real_content_object, request), name="images"), ImageScaling
)
```

For a `RealContentListingObject` wrapper, assert the brain view delegates to the
real object rather than raising; construct it with
`RealContentListingObject(real_content_object)`.

## 8. Items not verified

- I did not run a live Zope/Plone instance. The acquisition edge case where a
  brain could acquire a `__provides__` declaring `IImageScaleTraversable` from an
  ancestor was not exercised; no Plone core class or `alsoProvides` call was
  found that does this, and the existing absence of `@@images` on brains is
  consistent with no such provision.
- I did not verify the exact value/type of `brain.modified` for every content
  type (catalog `DateIndex` vs `_p_mtime`). The catalog has a `modified` metadata
  column (`catalog.xml:231`), but a live 6.2 instance was not available.
- I did not run `plone.namedfile`'s own test suite; the test layer includes
  `plone.namedfile` only, so whether `plone.app.contentlisting` is importable in
  that environment by default is unverified. The conditional registration makes
  this irrelevant for production and allows tests to skip the wrapper case.
- Default-fieldname selection on a brain with multiple `image_scales` keys is a
  design question; the catalog metadata has no `IPrimaryFieldInfo` equivalent.
  This ticket only confirms registration and lookup.

## Sources

Local:

- `src/plone/namedfile/scaling.zcml:12-18` — existing `@@images` page.
- `src/plone/namedfile/scaling.zcml:33-39` — `NavigationRootScaling` page.
- `src/plone/namedfile/scaling.py:886-985` — `NavigationRootScaling`.
- `src/plone/namedfile/scaling.py:94-110` — `ImageScale` requires a `data` object.
- `src/plone/namedfile/scaling.py:451-462` — `ImageScaling` and its view class.
- `src/plone/namedfile/adapters.py:49-78`, `112-116`, `131-136` —
  `image_scales` metadata shape and relative `download`.
- `src/plone/namedfile/interfaces.py:47-50` — `IImageScaleTraversable` marker.
- `src/plone/namedfile/testing.zcml:23-31` — test permission and marker setup.

Upstream:

- Plone 6.2 constraints:
  <https://dist.plone.org/release/6.2-dev/constraints.txt>
  (`plone.app.contentlisting==4.0.0`, `Products.ZCatalog==7.4`, `Zope==6.2`,
  `zope.browserpage==6.0`, `zope.configuration==7.1`).
- `plone.app.contentlisting` 4.0.0:
  <https://github.com/plone/plone.app.contentlisting/blob/4.0.0/src/plone/app/contentlisting/catalog.py#L15-L70>,
  <https://github.com/plone/plone.app.contentlisting/blob/4.0.0/src/plone/app/contentlisting/realobject.py#L16-L54>,
  <https://github.com/plone/plone.app.contentlisting/blob/4.0.0/src/plone/app/contentlisting/configure.zcml#L37-L45>.
- `Products.ZCatalog` 7.4:
  <https://github.com/zopefoundation/Products.ZCatalog/blob/7.4/src/Products/ZCatalog/CatalogBrains.py#L27-L49>,
  <https://github.com/zopefoundation/Products.ZCatalog/blob/7.4/src/Products/ZCatalog/interfaces.py#L253-L285>.
- `zope.browserpage` 6.0:
  <https://github.com/zopefoundation/zope.browserpage/blob/6.0/src/zope/browserpage/metaconfigure.py#L115-L190>.
- `zope.configuration` 7.1 (`installed` condition):
  <https://github.com/zopefoundation/zope.configuration/blob/7.1/src/zope/configuration/xmlconfig.py#L398-L413>.
- CMFPlone catalog metadata:
  <https://github.com/plone/Products.CMFPlone/blob/master/src/Products/CMFPlone/profiles/default/catalog.xml#L214-L231>,
  <https://github.com/plone/Products.CMFPlone/blob/master/src/Products/CMFPlone/image_scales/indexer.py>.
- REST API:
  <https://github.com/plone/plone.restapi/blob/main/src/plone/restapi/serializer/summary.py#L57-L100>,
  <https://github.com/plone/plone.restapi/blob/main/src/plone/restapi/serializer/blocks.py#L80-L94>.
- Volto:
  <https://github.com/plone/volto/blob/main/packages/volto/src/components/theme/Image/Image.jsx#L34-L75>.
- `cs.srcset`:
  <https://github.com/codesyntax/cs.srcset/blob/main/src/cs/srcset/configure.zcml>,
  <https://github.com/codesyntax/cs.srcset/blob/main/src/cs/srcset/helper.py>.
