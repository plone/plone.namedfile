---
id: D6
title: "Design metadata-backed picture()"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R2, R3]
---

## Question

Design the metadata-backed `picture()` path.

Decide:

- Extend `Img2PictureTag` with a scale/URL resolver, or add a new builder for
  metadata-backed sources.
- How to handle `sourceset`, `additionalScales`, `media`, `sizes`, `lazy`,
  width/height, class, alt, and title.
- How to resolve scale URLs without `uuidToObject()` or `@@images` traversal.
- What happens when a variant requests a scale that is missing from metadata.
- Which cases fall back to the object and which return `None`.
- The exact expected `<picture>` HTML to test.

Inputs: "Map image_scales metadata lifecycle and staleness" and "Assess
metadata-only picture() feasibility".

Output: the design, fallback rules, and at least one exact expected
`<picture>` snippet.

## Resolution

### Shared builder with a resolver hook

Extend `Img2PictureTag.create_picture_tag()` additively:

```python
def create_picture_tag(
    self,
    sourceset,
    attributes,
    uid=None,
    fieldname=None,
    resolve_urls=False,
    lazy=True,
    scale_resolver=None,
):
    ...
```

- `scale_resolver=None` keeps the existing object-backed behavior byte-for-byte:
  `uuidToObject()` plus `obj.unrestrictedTraverse("@@images")`.
- When `scale_resolver` is provided, it replaces both of those calls. It is
  called as `scale_resolver(scale_name)` and returns
  `{"url": ..., "width": ..., "height": ...}` or `None`.
- `uid` is not required when a resolver is supplied; `attributes["src"]`
  already satisfies the builder's `uid`/`src` guard.
- `resolve_urls` remains the legacy switch and is ignored for URL resolution
  when `scale_resolver` is present.
- Existing `picture.py` tests must pass without changes, proving the object
  path is untouched.

### Brain `picture()` flow

1. Resolve the field and metadata entry (field-resolution ticket). No entry ->
   return `None`.
2. Look up `picture_variant` in `get_picture_variants()`.
   - Unknown variant: log the same warning as the object view, choose the
     variant name as a scale when it exists in `available_sizes`, and delegate
     to `self.tag(...)`. This uses the metadata tag path and its fallback rules;
     no object wake is forced.
3. `sourceset = config["sourceset"]`; target scale is
   `sourceset[-1]["scale"]`. Mirror the object view if `sourceset` is empty.
4. **Preflight** every required scale:
   - per source: `target` plus `additionalScales`; when `additionalScales` is
     omitted, all allowed scales except the target;
   - only scales that have a registry width are required (the builder skips
     unknown names with a warning, exactly like the object path);
   - every required name must exist in the field's metadata `scales`, and the
     target must have `download`, `width`, and `height`.
   - If anything is missing, fall back the **whole** `picture()` call to the
     object view with the same arguments. This is expected for images smaller
     than the variant's largest requested scale.
5. Build attributes like the object view:
   - `class`: `[css_class]` when given, omitted when empty;
   - `src`: target metadata URL (satisfies the builder guard);
   - `width`/`height`: target metadata actual dimensions;
   - `title`: `_marker` -> normalized brain `Title`; truthy explicit value ->
     use it;
   - `alt`: only when truthy.
6. Call:

```python
Img2PictureTag().create_picture_tag(
    sourceset,
    attributes,
    fieldname=fieldname,
    resolve_urls=False,
    lazy=lazy,
    scale_resolver=resolver,
).prettify()
```

where `resolver(scale_name)` reads the metadata scale entry and returns the URL
via `_scale_url_from_download()` plus its actual `width`/`height`.

### Parity rules

- `w` descriptors come from `get_scale_width()` / `IAvailableSizes`, **not**
  metadata actual widths.
- The default `sizes` value uses the source target's registry width, matching
  `Img2PictureTag`.
- `media`, explicit `sizes`, `additionalScales`, `class="captioned"`, and
  `loading="lazy"` follow the existing builder.
- The `<img>` `width`/`height` use the metadata target scale's actual
  dimensions.
- If a resolver unexpectedly returns `None` after preflight, log a warning and
  skip that scale, matching the builder's missing-width behavior.

### Zero-wake guarantee

When preflight passes, `picture()` must not call `uuidToObject()`,
`getObject()`, or `unrestrictedTraverse("@@images")`. On preflight failure it
delegates through the fallback helper from the view-class ticket and wakes by
design.

### Documentation

Document that `picture()` is metadata-only only when every variant scale exists
in the catalog snapshot; otherwise it falls back to the object for exact
parity. Small originals commonly take the fallback because metadata omits
scales wider than the original.

