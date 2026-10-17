# Specification: brain-aware `@@images`

Status: draft for approval.
Map: [`MAP.md`](MAP.md).
Test plan: [`TEST-PLAN.md`](TEST-PLAN.md).

## 1. Summary

Add a brain-aware `@@images` view to `plone.namedfile`. It exposes the same
developer-facing API as the object-backed view (`scale`, `tag`, `srcset`,
`picture`, `getImageSize`, `available_sizes`, `modified`), but can be adapted
from a catalog brain or a `plone.app.contentlisting` wrapper. It answers from
the catalog's `image_scales` metadata first and falls back to the real object
only when metadata cannot answer. The metadata path performs no `getObject()`
calls.

The feature is additive: existing object-backed `@@images` registrations and
behavior are unchanged.

## 2. Goals

- Make the `@@images` API usable in listings without waking every object.
- Cover plain ZCatalog brains and `plone.app.contentlisting` wrappers.
- Preserve output parity with the object-backed view wherever metadata can
  answer.
- Make every fallback, divergence, and security limitation explicit.
- Ship tests, documentation, and a towncrier fragment with the code.

## 3. Non-goals

- URL traversal/serving of `@@images` on brains. Brains are not
  URL-addressable; generated scale URLs resolve on the real object.
- Editing or uploading image fields through a brain view.
- A multi-image/relation-list API beyond the first metadata entry.
- Replacing or modifying `cs.srcset`, `@@image_helper`, `@@images-srcset`, or
  `NavigationRootScaling`/`@@image_scale`.
- Plone 6.1 or earlier.
- GitHub issues, comments, PRs, pushes, or releases.
- A version bump; the release manager decides the release version.

## 4. Terminology

- **Brain**: a ZCatalog result implementing
  `Products.ZCatalog.interfaces.ICatalogBrain`.
- **Contentlisting wrapper**: an
  `plone.app.contentlisting.interfaces.IContentListingObject`, either
  `CatalogContentListingObject` (metadata-backed) or
  `RealContentListingObject` (real-object-backed).
- **Metadata origin**: the `ICatalogBrain` behind a plain brain or a catalog
  contentlisting wrapper.
- **Metadata path**: the branch that answers from `brain.image_scales` and does
  not call `getObject()`.
- **Fallback path**: the branch that obtains the real object and delegates to
  the object-backed `@@images`.
- **Wake-up**: any call that materializes the content object, including
  `brain.getObject()` and `_unrestrictedGetObject()`.
- **Original entry**: the top-level metadata dict for a field (`download`,
  `width`, `height`, `content-type`, `filename`).
- **Scale entry**: one entry in `image_scales[field][0]["scales"]`, with
  `download`, `width`, `height`.
- **HiDPI**: the old-style 2x/3x `srcset` produced by
  `getHighPixelDensityScales()`; it is not present in catalog metadata.

## 5. Public API

### 5.1 View and registration

New module: `src/plone/namedfile/brain_scaling.py`.

- `BrainImageScaling(ImageScaling)`.
- `BrainImageScale(ImageScale)` (see 5.4).

New ZCML file `src/plone/namedfile/brain_scaling.zcml`, included from
`configure.zcml`. `scaling.zcml` is not edited.

```xml
<browser:page
    name="images"
    for="Products.ZCatalog.interfaces.ICatalogBrain"
    class=".brain_scaling.BrainImageScaling"
    allowed_attributes="scale tag srcset picture getImageSize available_sizes modified"
    permission="zope2.View"
    />

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

- The existing `images` page for `IImageScaleTraversable` stays unchanged.
- No browser layer is required.
- Programmatic use:

```python
from zope.component import getMultiAdapter

images = getMultiAdapter((brain_or_wrapper, request), name="images")
tag = images.tag("image", scale="teaser")
```

- The `IContentListingObject` registration is conditional because
  `plone.app.contentlisting` is not a dependency of `plone.namedfile`.
- `brain_scaling.py` must stay import-safe without `plone.app.contentlisting`;
  do not import that package at module top level.
- Do not register `for="*"`.

### 5.2 Context resolution

`BrainImageScaling` resolves the metadata origin without waking:

```python
origin = (
    context.getDataOrigin()
    if hasattr(context, "getDataOrigin")
    else context
)
is_metadata = ICatalogBrain.providedBy(origin)
```

- Plain brain: metadata origin.
- `CatalogContentListingObject`: `getDataOrigin()` returns the brain unless the
  wrapper was already woken; check `ICatalogBrain.providedBy()`.
- `RealContentListingObject`: origin is a real object; use the object path.
- Never call `getObject()` to decide whether the context is a brain.

Object fallback:

```python
obj = origin.getObject() if ICatalogBrain.providedBy(origin) else origin
object_view = getMultiAdapter((obj, request), name="images")
```

Only a brain origin needs the waking `getObject()` call. The real content object
resolves to the existing `ImageScaling`.

### 5.3 Traversal

The brain view does not serve bytes:

- `publishTraverse(request, name)` raises `NotFound`.
- `traverse(name, furtherPath)` raises `TraversalError`.
- `browserDefault(request)` raises `BadRequest` with a clear message.

The generated scale URLs still point at the real object, where normal serving
applies.

### 5.4 Methods

```python
def scale(
    self,
    fieldname=None,
    scale=None,
    height=None,
    width=None,
    mode="scale",
    pre=False,
    include_srcset=None,
    **parameters,
): ...

def tag(
    self,
    fieldname=None,
    scale=None,
    height=None,
    width=None,
    mode="scale",
    include_srcset=None,
    **kwargs,
): ...

def srcset(
    self,
    fieldname=None,
    scale_in_src="huge",
    sizes="",
    alt=_marker,
    css_class=None,
    title=_marker,
    **kwargs,
): ...

def picture(
    self,
    fieldname=None,
    picture_variant=None,
    alt=None,
    css_class=None,
    title=_marker,
    lazy=True,
    **kwargs,
): ...

def getImageSize(self, fieldname=None): ...
def modified(self, fieldname=None): ...
```

`available_sizes` is inherited from `ImageScaling`. `getAvailableSizes` and
`getHighPixelDensityScales` are inherited as-is.

### 5.5 Scale object

`BrainImageScale(ImageScale)`:

- Constructor keyword metadata: `fieldname`, `scale`, `download`, `width`,
  `height`, `content_type`, `filename`.
- `context` is the metadata origin.
- `data = None`.
- `url`: `download` unchanged for `http://`, `https://`, or `/...`, otherwise
  `origin.getURL().rstrip("/") + "/" + download.lstrip("/")`; query strings and
  fragments are preserved.
- `width`, `height`: metadata values.
- `contentType` and `mimetype`: the field's `content-type`.
- `filename`: metadata filename.
- `srcset = []`; no `uid` attribute.
- `__name__`: `<fieldname>.<ext>` for the original,
  `<fieldname>-<scale>.<ext>` for a named scale.
- `tag` is overridden. `ImageScale.tag` eagerly evaluates `self.data._height`
  and `self.data._width` as default arguments, which fails with `data=None`; the
  brain scale uses its metadata dimensions and builds the same attribute list.
- `title` normalizes a callable `Title` (contentlisting) and a plain `Title`
  value (brain); missing -> `""`.
- `srcset_attribute()` returns `""`.
- `validate_access()` is a no-op on the metadata path.
- `index_html()`, `HEAD()`, and `set_headers()` raise `NotFound`.
- `absolute_url()` is inherited and returns `url`.
- Document that `.data` is `None` and `.uid` is absent.

## 6. Metadata contract

`brain.image_scales[fieldname]` is a list of dicts:

```python
{
    "filename": str | None,
    "content-type": str,
    "size": int,
    "download": str,
    "width": int,
    "height": int,
    "scales": {
        name: {"download": str, "width": int, "height": int},
    },
}
```

- `Missing.Value` means no images were indexed.
- `scales` contains only configured allowed sizes whose width is less than or
  equal to the original width. Scales wider than the original are absent.
- The original image is the top-level `download`/`width`/`height`; it is not
  repeated in `scales`.
- Metadata is written on catalog metadata updates (`reindexObject()` etc.) via
  `pre_scale`. It is a snapshot and can be stale.
- Metadata contains no HiDPI 2x/3x data and no storage UID beyond the one
  embedded in `download`.
- Reading `brain.image_scales` does not wake the object and does not perform a
  per-object permission check.

### Schema-aware no-metadata rule

- If the catalog schema contains `image_scales`, `Missing.Value`, a missing
  field, or an empty entry list means **no image**: return empty results
  without waking.
- If the catalog schema lacks `image_scales`, fall back to the object for every
  request.
- The schema check must not call `getObject()`.

## 7. Field resolution

One resolver is used by `scale`, `tag`, `srcset`, `picture`, and
`getImageSize`:

- Explicit `fieldname`: use it only if it exists in the metadata with a
  non-empty entry list; otherwise `(None, None)`.
- Omitted `fieldname`: use the only field when `image_scales` has exactly one
  key. Zero or multiple keys -> `(None, None)` plus a debug log listing the
  candidates.
- Do not prefer a field named `image`.
- Do not use `IPrimaryFieldInfo` or `getObject()` to find a primary field.
- Multiple entries for one field: use `entries[0]`; debug-log the count. Only
  the first image is supported.
- `(None, None)` means no image: `scale`/`tag`/`srcset`/`picture` return
  `None`; `getImageSize` returns `(0, 0)`.
- `modified` ignores `fieldname` on the metadata path.
- `available_sizes` ignores `fieldname`.

## 8. Fallback matrix

| Request | Behavior |
|---|---|
| `scale` name present in metadata `scales` | metadata |
| `scale` name in `available_sizes` but absent from metadata | fallback |
| `scale` name not in `available_sizes` | `None` (same as the object view) |
| `scale=None`, no dimensions | original metadata entry |
| explicit dimensions matching a metadata scale or the original | metadata |
| explicit dimensions matching nothing | fallback |
| `scale` plus explicit dimensions | take the scale, ignore dimensions (object behavior) |
| `mode != "scale"` | fallback |
| `pre=True` with metadata-answerable dimensions | metadata |
| `include_srcset=True` and HiDPI configured | fallback |
| `include_srcset=None` or `False` | metadata, no HiDPI |
| malformed metadata (missing `download`/`width`/`height`, wrong types) | fallback |
| `getObject() is None` | `None` / `(0, 0)` / `0`, no warning |
| `getObject()` raises `Unauthorized` | propagate from every method |
| stale metadata URL that later 404s | accepted and documented; no fallback |
| catalog schema lacks `image_scales` | fallback for every request |

**Exception:** `srcset()` bulk iteration skips a configured scale missing from
metadata and emits the rest. Only a missing selected `scale_in_src` falls back.
See 8.3.

The metadata path performs zero `getObject()`/`_unrestrictedGetObject()` calls
for every row marked "metadata". `available_sizes`,
`getHighPixelDensityScales`, and the schema check do not wake.

Fallbacks log at debug level with the fieldname, requested scale/dimensions,
and reason. No warnings for normal fallbacks.

## 9. Behavior by method

### 9.1 `scale()`

- Resolve field and metadata entry.
- If metadata can answer, return `BrainImageScale`.
- If the fallback matrix says fallback, delegate to the object-backed
  `scale()` with the same arguments.
- `include_srcset` behavior is in section 10.
- The returned scale for a metadata answer exposes the surface in 5.5.

### 9.2 `tag()`

- `include_srcset` is consumed, never rendered as an HTML attribute.
- Metadata path: resolve the scale and return `scale.tag(**kwargs)`.
- Fallback path: delegate to the object-backed `scale(..., pre=True)` and then
  `.tag(**kwargs)`.
- `include_srcset=True` with HiDPI configured uses the object-backed
  `scale(..., pre=True, include_srcset=True)` and returns its tag.
- Attribute behavior matches `ImageScale.tag`: `src`, `alt`, `title`, `height`,
  `width`, `class`, plus caller kwargs.

### 9.3 `srcset()`

Algorithm:

1. Resolve the field and original entry. No entry -> `None`.
2. Original width/height from metadata. Missing/zero -> fallback.
3. `available_widths = {width for width, height in available_sizes.values()}`.
4. If `original_width` is not an available width, prepend the original URL and
   `original_width w`. Missing `download` -> fallback.
5. Iterate `available_sizes.items()` in registry order. For every configured
   width `<= original_width`:
   - present in metadata `scales`: append its URL and its actual metadata
     `width` as the descriptor;
   - missing from metadata: skip it, debug-log, continue. Do not fall back.
6. Attributes mirror the object view:
   - `title`: `_marker` -> normalized brain `Title`; truthy explicit value ->
     use it; otherwise omit.
   - `alt`: `_marker` -> title; otherwise the given value.
   - `css_class` -> `class` when not `None`.
   - Apply `kwargs` after defaults.
   - Always emit `sizes` (default `""`).
   - Emit `srcset` as comma-space joined URLs (empty string when no URLs).
7. Resolve `scale_in_src`:
   - if absent from `available_sizes`, take the first available scale whose
     width `<= original_width`; if none, return `None`;
   - if the chosen scale is missing from metadata, fall back the whole call;
   - set `src`, and set `width`/`height` from the scale unless the caller
     supplied them.
8. Return `_image_tag_from_values(*attributes.items())`.

Documented divergence: the bulk iteration can produce a shorter `srcset` than
the object view when metadata is incomplete.

### 9.4 `picture()`

1. Resolve the field and entry. No entry -> `None`.
2. Look up `picture_variant` in `get_picture_variants()`.
   - Unknown variant: log the same warning as the object view; use the variant
     name as a scale when it exists in `available_sizes`, then delegate to
     `self.tag(...)`.
3. `sourceset = config["sourceset"]`; target scale is
   `sourceset[-1]["scale"]`.
   - Empty `sourceset`: log a warning and return `None` (defensive; the object
     view raises `IndexError`, but a registry misconfiguration should not break
     a listing).
4. Preflight every required scale:
   - per source: target plus `additionalScales`; when `additionalScales` is
     omitted, all allowed scales except the target;
   - only names with a registry width are required; the builder skips unknown
     names with a warning, like the object path;
   - every required name must exist in the metadata `scales`, and the target
     must have `download`, `width`, and `height`.
   - Any miss -> fall back the whole `picture()` call with the same arguments.
5. Build attributes:
   - `class`: `[css_class]` when given, omitted when empty;
   - `src`: target metadata URL;
   - `width`/`height`: target metadata actual dimensions;
   - `title`: `_marker` -> normalized brain `Title`; truthy explicit value ->
     use it;
   - `alt`: only when truthy.
6. Call `Img2PictureTag().create_picture_tag(..., resolve_urls=False,
   lazy=lazy, scale_resolver=resolver).prettify()`, where `resolver(scale_name)`
   returns the metadata URL and actual dimensions.

`Img2PictureTag.create_picture_tag` gains an optional `scale_resolver` hook.
When it is `None`, the object path is unchanged. When it is provided, it
replaces `uuidToObject()` and `unrestrictedTraverse("@@images")`.

Parity rules:

- `w` descriptors come from `IAvailableSizes`, not metadata actual widths.
- Default `sizes` uses the source target's registry width.
- `media`, explicit `sizes`, `additionalScales`, `class="captioned"`, and
  `loading="lazy"` follow the existing builder.
- `<img>` dimensions use the metadata target's actual dimensions.
- A resolver returning `None` after preflight logs a warning and skips that
  scale.

Documented divergence: `picture()` falls back to the object when any required
scale is absent. Small originals commonly fall back because metadata omits
scales wider than the original.

### 9.5 `getImageSize()`

- Field present with metadata dimensions -> those values.
- Field present but dimensions missing/corrupt -> fallback.
- Field absent -> `(0, 0)`.
- Omitted fieldname -> field resolution rules.
- `Unauthorized` from the fallback propagates.

### 9.6 `modified()`

- Return `DateTime(brain.modified).millis()` when available; otherwise `0`.
- Ignore `fieldname` on the metadata path.
- Do not fall back just to read `_p_mtime`.

### 9.7 `available_sizes`

Inherited registry lookup; `fieldname` is ignored.

## 10. HiDPI

`include_srcset` is a named keyword on brain `scale()` and `tag()`; `tag()`
passes it through.

| Call | HiDPI configured | Behavior |
|---|---|---|
| `include_srcset=None` (default), any `pre` | either | metadata; no HiDPI; no wake |
| `include_srcset=False` | either | metadata; no HiDPI; no wake |
| `include_srcset=True` | no | metadata; no HiDPI; no wake |
| `include_srcset=True` | yes | fall back to the object `scale()`/`tag()`; wake by design |

`None` deliberately ignores the object's “`pre=True` implies include” rule.
`getHighPixelDensityScales()` is a registry read and does not wake. Do not
synthesize 2x/3x URLs from metadata.

`srcset()` and `picture()` do not accept `include_srcset` and remain
HiDPI-free.

## 11. Security

- The metadata path performs no extra permission check. Document that this is
  the same exposure as today's catalog/REST `image_scales` output.
- Generated scale URLs resolve to the real object and enforce `View` there.
  Rendering a tag does not grant access to the bytes.
- Field-level read permissions are **not** enforced on the metadata path. The
  object-backed view uses `guarded_getattr`; the brain view does not. Protected
  image fields must use the object-backed view.
- `getObject() is None` -> empty results, no warning.
- `getObject()` raises `Unauthorized` -> propagate from every method, including
  `getImageSize`. Do not convert it to an empty result.
- `RealContentListingObject` and already-woken wrapper origins use the object
  path and keep normal enforcement.
- Do not log permission failures at info/warning level or include user
  identities/roles in fallback messages.
- No `guarded` mode; stricter behavior is a custom view or the object-backed
  view.

## 12. Compatibility and implementation surface

New/changed files:

- `src/plone/namedfile/brain_scaling.py` — `BrainImageScaling`,
  `BrainImageScale`, helpers.
- `src/plone/namedfile/brain_scaling.zcml` — registrations.
- `src/plone/namedfile/configure.zcml` — include the new ZCML.
- `src/plone/namedfile/picture.py` — additive `scale_resolver` hook on
  `Img2PictureTag.create_picture_tag`.
- `src/plone/namedfile/testing.py` — Plone integration/functional layers.
- `src/plone/namedfile/tests/test_brain_images.py`,
  `tests/test_brain_images_functional.py`,
  `tests/brain_images_helpers.py`.
- `docs/brain-images.rst`, `README.rst`, `setup.py` long_description,
  `news/brain-images.feature`.

No changes to:

- `ImageScaling` behavior or the existing `images` registration.
- `scaling.zcml`.
- `NavigationRootScaling`/`@@image_scale`.
- `cs.srcset`/`@@image_helper`/`@@images-srcset`.
- `CHANGES.rst` (towncrier writes it).
- The version in `setup.py` (`8.1.2.dev0`).

Backward compatibility:

- Existing object-backed lookups resolve to `ImageScaling` as before.
- Existing `Img2PictureTag` calls without `scale_resolver` behave identically.
- New `images` pages are additive and keyed by different `for` interfaces.
- An add-on that registers `images` for the same `for` interface would
  conflict at ZCML time, as with any `browser:page`.

## 13. Documentation, changelog, and release

- New `docs/brain-images.rst`, included in `long_description` between
  `CHANGES.rst` and `usage.rst`.
- README section linking to the docs with an absolute GitHub URL.
- `news/brain-images.feature`; no manual `CHANGES.rst` edit.
- No version bump; the release manager chooses the next minor.
- No PyPI upload, GitHub release, push, or PR.
- Implementation stays on the local `brain-images` branch.

Docs must cover the API, examples, fallback contract, field resolution, HiDPI,
security caveats, divergences, non-goals, and Plone 6.2 scope.

## 14. Testing

The full plan is [`TEST-PLAN.md`](TEST-PLAN.md). Acceptance requires:

- package-local Plone integration and functional layers;
- brain/object parity for `scale`, `tag`, `srcset`, and `picture`;
- zero `getObject()`/`_unrestrictedGetObject()` on metadata paths, with a
  positive-control test;
- field resolution, fallback matrix, HiDPI, security, and stale/malformed
  metadata cases;
- functional URL serving and unauthorized access;
- regression coverage for the object-backed view and `picture.py`;
- `tox -e py312-plone62` and the repository's Plone 6.2 Python matrix green.

## 15. Implementation outline (to be ticketed after approval)

These are not tickets yet; they graduate after this specification is approved.

1. Add the Plone test layer and fixture helpers; verify the baseline.
2. Implement the metadata origin resolver, schema-aware check, and field
   resolver.
3. Implement `BrainImageScale` and the URL helper.
4. Implement `BrainImageScaling.scale`, `tag`, `getImageSize`, `modified`, and
   the fallback delegation.
5. Implement `srcset()` with the skip-missing divergence.
6. Add the `Img2PictureTag` resolver hook and `picture()`.
7. Implement HiDPI `include_srcset` behavior.
8. Implement traversal refusal and security behavior.
9. Write the tests from `TEST-PLAN.md`.
10. Write docs, README section, news fragment, and packaging updates.
11. Run the full suite and lint; prepare the local `brain-images` branch.

## 16. Risks and documented divergences

- **Stale metadata**: a catalog snapshot can point at a scale URL that 404s
  after storage cleanup. The view does not detect this; the URL may 404 until
  the scale is regenerated.
- **Original-image URL**: an object-backed `scale()`/`tag()` with no dimensions
  uses the storage `image-0` UID URL. The metadata view uses the indexed
  original `image-<width>` URL. Both serve the original image; parity tests
  compare the metadata original against the object call with explicit original
  dimensions.
- **Small images and `picture()`**: metadata omits scales wider than the
  original, so many small images fall back to the object; parity is preserved
  at the cost of a wake-up.
- **`srcset()` completeness**: missing configured scales are skipped, so brain
  output can be shorter than object output.
- **Field-level permissions**: not enforced on the metadata path.
- **Custom scale URLs**: a request-dependent `_scale_url` override can differ
  from the URL captured at index time.
- **Contentlisting wrapper already awake**: `getDataOrigin()` can return the
  real object; the view then uses the object path.
- **Optional contentlisting**: the wrapper registration depends on
  `plone.app.contentlisting`; plain brains work without it.
- **Catalog without `image_scales`**: every request falls back to the object.
- **HiDPI**: omitted by default; explicit opt-in wakes the object.

## 17. Acceptance criteria

- A plain brain and a catalog contentlisting wrapper resolve
  `getMultiAdapter((item, request), name="images")` to `BrainImageScaling`.
- A real content object still resolves to `ImageScaling`.
- `scale`, `tag`, `srcset`, and `picture` match the object output for in-sync
  metadata, with the documented divergences.
- Metadata paths make zero `getObject()`/`_unrestrictedGetObject()` calls.
- The fallback matrix, field resolution, HiDPI, security, and stale/malformed
  cases are covered by tests.
- The existing suite and `picture.py` tests are green.
- Docs, README, long_description, and the news fragment are present.
- No GitHub writes, no version bump, no release.
