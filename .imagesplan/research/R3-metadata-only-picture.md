# R3 — Assess metadata-only `picture()` feasibility

Ticket: [003-assess-metadata-only-picture.md](../tickets/003-assess-metadata-only-picture.md)

Status: research complete. Sources read only; no code, map, or ticket changes
other than this file and the R3 ticket.

## Verdict

**Conditional yes.** A no-wake-up `picture()` can reproduce the object-backed
output **exactly** when every scale the variant would traverse is already in
`brain.image_scales[fieldname][0]["scales"]`.

That condition is narrower than it sounds. The catalog field adapter
deliberately **omits every configured scale whose width is larger than the
original image** (`src/plone/namedfile/adapters.py:86-93`). The object-backed
view does not omit them: it pre-registers a scale anyway (no upscaling of
pixels, but a distinct UID URL and its requested width descriptor). The
existing picture tests demonstrate this directly: the test image is 200x200
(`src/plone/namedfile/tests/image.png`, verified with PIL), yet the expected
`medium` output contains 600w, 800w, 1000w, and 1200w sources
(`src/plone/namedfile/tests/test_scaling.py:536-558`). Those scales cannot exist
in that image's catalog metadata.

Consequences:

- Default `large` variant (target `larger` 1000, additional up to `huge` 1600)
  only has exact metadata parity for originals at least 1600 px wide.
- Default `medium` (target `teaser` 600, additional up to `great` 1200) only for
  originals at least 1200 px wide.
- Default `small` (target `preview` 400, additional up to `larger` 1000) only for
  originals at least 1000 px wide.
- Custom variants whose `additionalScales` are all at or below the original
  width can have parity for smaller images.

**Recommendation:** implement a metadata fast path with a preflight "all
required scales present" gate. If the gate passes, render fully from metadata.
If it fails, use an explicit, documented object fallback (`getObject()` +
`@@images`) for parity. If zero wake-up is mandatory, degrade deliberately and
document that the HTML differs: either skip missing srcset entries or emit
legacy `@@images/<fieldname>/<scale>` URLs. Do not claim exact parity in that
degraded mode.

## Why metadata is enough when scales are present

`brain.image_scales` is a catalog snapshot written by
`Products.CMFPlone.image_scales.indexer.image_scales`
(`Products/CMFPlone 6.2.2`, `image_scales/indexer.py:9-22`). The content adapter
(`image_scales/adapters.py:13-33`) delegates each image field to
`plone.namedfile.adapters.ImageFieldScales`, which returns a list of dicts:

```python
{
    "filename": image.filename,
    "content-type": image.contentType,
    "size": image.getSize(),
    "download": self._scale_view_from_url(url),
    "width": width,
    "height": height,
    "scales": {
        name: {"download": ..., "width": actual_width, "height": actual_height},
        ...
    },
}
```

(`src/plone/namedfile/adapters.py:68-78, 80-118`)

Relevant properties:

- `download` is relative to the object URL: `@@images/<uid>.<ext>`, produced by
  stripping `context.absolute_url()` (`adapters.py:131-136`). It may be an
  absolute `http(s)` URL for custom scale URL implementations, because the
  replace is a no-op then.
- `scales[name]["width"/"height"]` are the **actual** dimensions from the same
  `pre_scale` info the object view uses (`adapters.py:97-116`).
- `scales` is built with `include_srcset=False`; HiDPI scales are not in it.
- The original is not repeated in `scales`; it is the top-level `download` plus
  top-level `width`/`height`.
- `scales` contains only configured `IAvailableSizes` names whose configured
  width is `<=` original width (`adapters.py:86-93`). Corrupt images may also be
  absent (`adapters.py:104-107`).

For a scale that is present, the UID is identical to the one the object view
would build: both paths call the same `pre_scale` with `fieldname`, `width`,
`height`, `mode`, and the same `modified` callable; `scale` is dropped from the
hash when width and height are given (`plone.scale 4.3.0`,
`plone/scale/storage.py:197-218, 221-267`). The catalog's `download` therefore
already *is* the URL the object-backed `picture()` would generate for that
scale. The existing metadata-only precedent in `NavigationRootScaling` uses the
same rule (`src/plone/namedfile/scaling.py:944-975`):

```python
src = (
    data["download"]
    if data["download"].startswith("http")
    else f"{brain.getURL()}/{data['download']}"
)
```

So a resolver replaces both `uuidToObject()` and
`obj.unrestrictedTraverse("@@images").scale(...)` for present scales:

```python
def scale_data(brain, fieldname, scale):
    entry = brain.image_scales[fieldname][0]
    return entry["scales"].get(scale)

def scale_url(brain, fieldname, scale):
    data = scale_data(brain, fieldname, scale)
    if data is None:
        return None
    download = data["download"]
    return download if download.startswith("http") else f"{brain.getURL()}/{download}"
```

No UID lookup, no object traversal, no request needed. `IAvailableSizes`
(`get_allowed_scales`) and `get_picture_variants` are registry utilities and do
not wake objects (`src/plone/namedfile/picture.py:17-30`).

## What `picture()` actually needs

Object-backed flow (`src/plone/namedfile/scaling.py:735-792`):

1. Look up the variant in `get_picture_variants()`. If absent, log and delegate
   to `tag()` (using `picture_variant` as a scale name if it exists in
   `available_sizes`).
2. `target = sourceset[-1]["scale"]`; call `scale(fieldname, target, pre=True)`.
   If `None`, return `None`.
3. Build attributes: optional class, `src` (unused later), target
   `width`/`height`, default title from `context.Title()`, optional alt.
4. Call `create_picture_tag(..., resolve_urls=True, uid=scale.context.UID(),
   fieldname=..., lazy=...)`.
5. `create_picture_tag` (`picture.py:48-130`):
   - For each source: `target_scale`, `media`, `sizes`.
   - `additionalScales` default: **all** allowed scales except the target.
   - For `[target] + additional`: descriptor width comes from
     `IAvailableSizes` (`get_scale_width`, `picture.py:38-46`), not metadata.
     If the name is not an allowed scale, warn and skip.
   - URL per scale: object path uses `@@images` traversal; metadata path uses
     `brain.getURL()` + relative `download`.
   - `sizes` default uses the source's target registry width.
   - Last source: img `src`/`width`/`height` from the target scale; `lazy`
     adds `loading="lazy"`; class/alt/title copied.
   - `picture` gets `class="captioned"` when `captioned` is in the class list.
   - Output is `.prettify()` from BeautifulSoup.

Inputs available without waking:

| Input | Source |
|---|---|
| variant config (`sourceset`, `additionalScales`, `media`, `sizes`) | `IImagingSchema.picture_variants` registry |
| allowed scale names and descriptor widths | `IAvailableSizes` registry |
| fieldname -> image entry | `brain.image_scales` |
| scale URL + actual dimensions | entry `scales[name]` / top-level `download`, `width`, `height` |
| base URL | `brain.getURL()` |
| default title | `brain.Title` (handle callable, as `NavigationRootScaling` does) |
| alt/class/lazy | call arguments |

Inputs **not** available from metadata:

- UID/hash URL for a scale absent from `scales` (upscaled, stale, corrupt,
  registry changed). The UID depends on the field's `modified` value and the
  exact scale parameters (`plone/scale/storage.py:197-218`); it is not derivable
  from `brain.modified` reliably. **This is the hard blocker for exact parity.**
- The primary fieldname when the caller omits `fieldname` and the brain has more
  than one image field. `IPrimaryFieldInfo` needs the object. If exactly one key
  exists it can be inferred; otherwise require an explicit fieldname or fall
  back.
- `context.Title()` in exotic/computed-title or multilingual cases. Catalog
  `Title` is the usual approximation; for `CatalogContentListingObject` it may
  be callable (`scaling.py:961-965`). Low risk, not zero.
- Whether the indexed scale still exists in storage. Metadata is a snapshot;
  after storage cleanup the URL may 404 even though the HTML is identical.
  The object path re-registers a placeholder while rendering; the metadata path
  does not (`plone.scale/storage.py:221-267` vs `301-333`). R2 covers staleness.
- Runtime state used by custom `_scale_url()` overrides. The adapter captured
  the URL at index time; a request-dependent override can differ later.

## Metadata-only algorithm

```python
def picture_from_brain(view, brain, fieldname=None, picture_variant=None,
                       alt=None, css_class=None, title=_marker, lazy=True,
                       **kwargs):
    variants = get_picture_variants()
    config = variants.get(picture_variant)
    if not config:
        # Current behavior: fall back to tag(). Use the metadata tag resolver;
        # if it cannot answer (including a missing scale), use object fallback.
        ...

    entry = resolve_entry(brain, fieldname)  # Missing.Value, list[0], inference
    if entry is None:
        return None                          # parity with empty/missing image

    allowed = get_allowed_scales()
    sourceset = config["sourceset"]
    target = sourceset[-1]["scale"]
    if target not in allowed:
        return None                          # object picture() returns None

    required = set()
    for source in sourceset:
        names = [source["scale"]]
        additional = source.get("additionalScales")
        if additional is None:
            additional = [n for n in allowed if n != source["scale"]]
        names += additional
        required.update(n for n in names if n in allowed)

    # Exact-parity gate. Missing because width > original, stale index,
    # corrupt image, or registry change -> metadata cannot reproduce the HTML.
    if not required.issubset(entry["scales"]):
        return OBJECT_FALLBACK               # documented wake-up, exact parity
        # Alternative if no-wake-up is mandatory: render only present names
        # (HTML differs) or use legacy URLs (HTML differs).

    target_data = entry["scales"][target]
    attributes = {}
    if css_class:
        attributes["class"] = [css_class]
    attributes["src"] = scale_url(brain, fieldname, target)  # ignored by builder
    attributes["width"] = target_data["width"]
    attributes["height"] = target_data["height"]
    if title is _marker:
        title = brain.Title
        if callable(title):
            title = title()
        attributes["title"] = title
    elif title:
        attributes["title"] = title
    if alt:
        attributes["alt"] = alt

    return build_picture(
        sourceset,
        attributes,
        allowed_scales=allowed,
        url_for=lambda name: scale_url(brain, fieldname, name),
        lazy=lazy,
    ).prettify()
```

Implementation should ideally extend `Img2PictureTag.create_picture_tag` with an
optional URL resolver (or extract a shared builder), so `media`, `sizes`,
`additionalScales`, empty-source quirks, `captioned`, and BeautifulSoup
normalization stay in one place. Do not fork the rendering logic.

## Missing-scale behavior, case by case

| Case | Object-backed behavior | Metadata-only behavior |
|---|---|---|
| Name not in `IAvailableSizes` | Target: `picture()` returns `None`. Non-last source: warning + skipped, source may be empty. | Same; no metadata needed. Preserve the warning/empty-source quirk. |
| Name in `IAvailableSizes`, absent from metadata because configured width > original | `pre_scale` creates a placeholder with a requested-width UID; URL is `@@images/<field>-<requested-width>-<hash>.<ext>`; actual width/height are the original dimensions. | UID/hash is unknown. **Cannot reproduce exactly.** Fallback or degrade. |
| Name in `IAvailableSizes`, absent due to stale index / cleared scales / corrupt image | Object path creates or reuses the scale now. | Same blocker as above. Fallback. |
| Name in metadata but no longer in `IAvailableSizes` | Object path skips it (no descriptor width). | Must also skip; do not render stale names. |
| Variant target missing from metadata | Object may still produce a scale. | Fallback; if no-wake-up is mandatory, choose original/largest present scale and document the difference. |
| `brain.image_scales` is `Missing.Value` / field absent | Object `picture()` returns `None` for empty field; if catalog is stale, object may still have an image. | Return `None` if authoritative; fallback if staleness must be handled. |
| Multiple image fields, `fieldname=None` | `IPrimaryFieldInfo` on the object. | Infer only if one key; else require explicit fieldname or fallback. |

## Parity risks beyond missing scales

- **Stale metadata**: catalog is updated only on reindex, not when
  `allowed_sizes`, `picture_variants`, or storage changes. The gate protects
  HTML parity but cannot guarantee the emitted URL still resolves; the object
  path re-registers placeholders during render. Document this as a known
  trade-off or check/fallback if strict.
- **Deleted/moved object**: the current code's `uuidToObject()` returns `None`,
  so it silently degrades to `update_src_scale()` legacy URLs **without**
  width/height attributes (`picture.py:94-99, 116-129`). A metadata path would
  keep emitting UID URLs. This is a behavior change in a broken-object edge
  case, not a normal-path parity issue.
- **Title**: catalog title vs `context.Title()`; handle callable brains as
  `NavigationRootScaling` does.
- **Custom `_scale_url()`**: metadata captured the URL at index time; a later
  request-dependent override is not represented.
- **HiDPI**: `picture()` ignores `ImageScale.srcset` and only uses
  `url`/`width`/`height`. HiDPI settings do **not** change the expected
  `<picture>` HTML, so this is not a blocker. The object path's pre-scale call
  creates HiDPI scales as a side effect; the metadata path need not.
- **BeautifulSoup attribute order**: tests already accept variation
  (`test_scaling.py:549-551`); `.prettify()` output is not a stable byte-for-byte
  contract across bs4 versions.

## Expected HTML snippets

### Object-backed medium variant (existing test, ellipsized)

From `src/plone/namedfile/tests/test_scaling.py:540-547`:

```html
<picture>
 <source...srcset="http://nohost/item/@@images/image-600-....png 600w,
http://nohost/item/@@images/image-400-....png 400w,
http://nohost/item/@@images/image-800-....png 800w,
http://nohost/item/@@images/image-1000-....png 1000w,
http://nohost/item/@@images/image-1200-....png 1200w".../>
 <img...src="http://nohost/item/@@images/image-600-....png".../>
</picture>
```

with asserted `height="200"`, `width="200"`, `title="foo"`,
`loading="lazy"`, and the default sizes string
`(min-width: 576px) 600px, (min-width: 768px) 600px, 98vw`.

### Metadata-backed, all required scales present

Replaying `create_picture_tag` with the test's scales and variant config,
substituting metadata `download` URLs, produces (UIDs shortened to `<hash>`;
attribute order is bs4-dependent):

```html
<picture>
 <source sizes="(min-width: 576px) 600px, (min-width: 768px) 600px, 98vw" srcset="http://nohost/item/@@images/image-600-<hash>.png 600w,
http://nohost/item/@@images/image-400-<hash>.png 400w,
http://nohost/item/@@images/image-800-<hash>.png 800w,
http://nohost/item/@@images/image-1000-<hash>.png 1000w,
http://nohost/item/@@images/image-1200-<hash>.png 1200w"/>
 <img height="600" loading="lazy" src="http://nohost/item/@@images/image-600-<hash>.png" title="foo" width="600"/>
</picture>
```

`width`/`height` here are the target scale's metadata dimensions. In the
existing 200x200 fixture they are 200/200 because `mode="scale"` does not
upscale; the URL still says `image-600-...`.

### Metadata-only degraded mode, 900 px original, `medium`

Metadata for a 900 px wide image contains `teaser`, `preview`, `large` (and
smaller), but not `larger` (1000) or `great` (1200). If the policy is "skip
missing", the srcset loses two entries and is not parity:

```html
<picture>
 <source sizes="(min-width: 576px) 600px, (min-width: 768px) 600px, 98vw" srcset="http://nohost/item/@@images/image-600-<hash>.png 600w,
http://nohost/item/@@images/image-400-<hash>.png 400w,
http://nohost/item/@@images/image-800-<hash>.png 800w"/>
 <img height="600" loading="lazy" src="http://nohost/item/@@images/image-600-<hash>.png" title="foo" width="600"/>
</picture>
```

The object-backed version would have two more lines (`1000w`, `1200w`). If the
policy is "fall back", the object-backed snippet is reproduced exactly.

For a 200x200 image with `medium`, the metadata has none of the requested
scales (`preview` 400 and up are all omitted), so the target itself is missing;
a `None` or object fallback is the only honest outcome. Skipping missing
entries would leave an empty `srcset` and require an arbitrary replacement
image.

## Recommendation for D6 (metadata-backed `picture()`)

1. Add a metadata resolver with `url_for(scale)` / `data_for(scale)` built on
   `brain.image_scales[fieldname][0]["scales"]` and `brain.getURL()`.
2. Refactor `Img2PictureTag` to accept that resolver instead of always doing
   `uuidToObject()` + `@@images` traversal. Keep one builder.
3. Preflight every scale the variant would traverse (source targets plus
   allowed `additionalScales`). If all are present, render metadata-only.
4. Otherwise fall back to the object-backed `picture()` by default. This is the
   only route to exact parity. Document that smaller-than-variant images,
   stale indexes, cleared storage, and post-index registry changes take the
   fallback.
5. If a zero-wake-up mode is required, define it as a separate documented,
   non-parity mode (skip missing entries or legacy URLs) and test the exact
   degraded HTML.
6. Require an explicit `fieldname` for multi-image brains; infer only when
   `len(brain.image_scales) == 1`. Preserve the variant-missing `tag()`
   fallback, default title/alt semantics, `captioned`, lazy, media, sizes, and
   the current behavior of ignoring `**kwargs` in the variant path.

## Evidence index

- `src/plone/namedfile/picture.py:17-30` — allowed scales / variants.
- `src/plone/namedfile/picture.py:38-46` — srcset widths come from registry.
- `src/plone/namedfile/picture.py:48-130` — builder, uuid lookup, traversal,
  default additionalScales/sizes, img attributes, lazy.
- `src/plone/namedfile/picture.py:132-159` — UID URL resolution and legacy
  `update_src_scale`.
- `src/plone/namedfile/scaling.py:533-542` — `available_sizes`.
- `src/plone/namedfile/scaling.py:619-688` — scale lookup/pre_scale.
- `src/plone/namedfile/scaling.py:735-792` — object-backed `picture()`.
- `src/plone/namedfile/scaling.py:886-986` — metadata-only precedent,
  including URL prefixing and callable title.
- `src/plone/namedfile/adapters.py:44-118` — metadata entry shape, actual
  dimensions, omission of scales wider than the original.
- `src/plone/namedfile/adapters.py:120-136` — original URL and relative
  `download`.
- `src/plone/namedfile/tests/test_scaling.py:536-699` — exact picture test
  expectations, including a 200 px image with 600–1200w srcsets.
- `src/plone/namedfile/tests/test_scaling.py:58-117` — test variants/scales.
- `src/plone/namedfile/tests/test_scaling_functional.py` — no `picture()` tests.
- `Products.CMFPlone 6.2.2 image_scales/indexer.py:9-22` — catalog metadata.
- `Products.CMFPlone 6.2.2 image_scales/adapters.py:13-33` — field aggregation.
- `plone.app.contentlisting 3.0.5 realobject.py:111-113` — listing wrapper
  rebuilds `image_scales` from the real object via the adapter (i.e. wrapper
  access can wake; a raw brain is the zero-wake-up source).
- `plone.scale 4.3.0 storage.py:197-218, 221-267, 301-333` — UID hash inputs,
  placeholder creation, lazy generation; confirms missing UIDs depend on
  `modified` and exact parameters.
- `plone.scale 4.3.0 scale.py:416-436` — `calculate_scaled_dimensions`;
  `mode="scale"` does not upscale, explaining requested-width UIDs with
  original dimensions.
- `plone.base 3.x controlpanel.py` (cache: 3.1.2 `IImagingSchema`) — default
  picture variants (`large` up to huge, `medium` up to great, `small` up to
  larger).
