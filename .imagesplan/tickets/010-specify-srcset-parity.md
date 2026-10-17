---
id: D5
title: "Specify srcset parity from metadata"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R1, R2]
---

## Question

Specify how the brain-aware `srcset()` reproduces the object-backed algorithm
from metadata.

Decide:

- Whether to include the original image when its width is not one of the
  available scales.
- Ordering, de-duplication, and inclusion of scales wider than the original.
- `scale_in_src` default (`huge`), fallback when it is absent, and the selected
  `src` scale.
- `<img>` width/height, `alt`/`title` defaults, `sizes`, `css_class`, and extra
  keyword attributes.
- URL construction from `download` and the brain URL.
- Any deliberate divergence, documented.

Inputs: "Verify brain view registration and resolution" and "Map image_scales
metadata lifecycle and staleness".

Output: the algorithm plus exact expected HTML cases for the test plan.

## Resolution

### Algorithm

`BrainImageScaling.srcset()` mirrors `ImageScaling.srcset()` except for the
documented skip-missing rule:

1. Resolve the field and metadata entry (field-resolution ticket). If there is
   no entry, return `None`.
2. Read `original_width`/`original_height` from the top-level metadata entry.
   If they are missing or zero, fall back to the object view (fallback matrix).
3. Build `available_widths` from `self.available_sizes.values()`.
4. If `original_width` is **not** an available width, prepend the original:
   `_scale_url_from_download(origin, entry["download"])` plus
   `f" {original_width}w"`. Missing `download` is a fallback trigger.
5. Iterate `self.available_sizes.items()` in registry order. For every scale
   whose configured width is `<= original_width`:
   - if the name exists in the field's metadata `scales`, append its URL plus
     `f" {scale['width']}w"` using the metadata entry's actual width;
   - if the name is missing from metadata, **skip it**, log at debug level, and
     continue. Do **not** fall back for this bulk-iteration case.
6. Build attributes exactly like the object view:
   - `title`: `_marker` -> normalized brain `Title`; truthy explicit value ->
     use it; otherwise omit.
   - `alt`: `_marker` -> the resolved title; otherwise the given value.
   - `css_class` -> `class` when not `None`.
   - Apply `kwargs` after the defaults, so caller attributes can override
     `title`/`alt`/`class`.
   - Always emit `sizes` (default `""`).
   - Emit `srcset` as the comma-space joined URLs (empty string when no URLs
     remain).
7. Resolve `scale_in_src`:
   - if it is not in `available_sizes`, choose the first available scale whose
     width is `<= original_width`; if none exists, return `None`;
   - if the chosen scale is missing from metadata, fall back the whole call to
     the object view (this is the one `srcset` case that falls back);
   - set `src` from that scale, and set `width`/`height` from it unless the
     caller already supplied them.
8. Return `_image_tag_from_values(*attributes.items())`.

### Explicit divergence

The bulk `srcset` iteration skips missing configured scales and emits the rest.
All other methods follow the fallback matrix and fall back when a requested
scale is absent. Document this difference: a `srcset` generated on a brain can
be shorter than the object-backed one when metadata is incomplete.

### URLs and text

- Use `_scale_url_from_download()` from the scale-object ticket for every URL.
- Do not consult storage, MIME types, or `getObject()` during a metadata-only
  run.
- Normalize a plain brain `Title` value and a callable contentlisting `Title`
  through one helper.

### Tests

- Exact HTML parity when metadata is in sync.
- A missing scale in the iteration produces a shorter `srcset`, not a fallback.
- A missing selected `scale_in_src` falls back to the object.
- Zero `getObject()` calls for the in-sync path.

