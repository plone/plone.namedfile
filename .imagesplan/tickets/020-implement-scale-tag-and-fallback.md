---
id: I4
title: "Implement scale, tag, accessors, and fallback delegation"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: [D11, I2, I3]
---

## Question

Implement the core metadata and fallback behavior from `SPEC.md` sections 8,
9.1, 9.2, 9.5, and 9.6.

Do:

1. Implement `scale()` with the metadata/fallback matrix:
   - named scales, original entry, exact dimensions, default mode,
     `pre=True`;
   - fallback for missing configured scales, arbitrary dimensions,
     non-default modes, and malformed metadata;
   - `scale` name not in `available_sizes` -> `None`;
   - `scale` plus dimensions takes the scale;
   - debug-level fallback logging.
2. Implement `tag()` using the metadata scale and preserving
   `ImageScale.tag` attribute behavior; consume `include_srcset` and never
   render it as an HTML attribute. The HiDPI fallback itself is completed in
   I7.
3. Implement `getImageSize()` and `modified()` per the spec.
4. Implement the object fallback through `_object_view`, including
   `getObject() is None` and `Unauthorized` behavior.
5. Keep the metadata path free of `getObject()` calls.
6. Add tests for parity, the fallback matrix, schema-aware no-metadata,
   `getImageSize`, `modified`, `Unauthorized`, and zero wake-ups with the
   positive control.

No GitHub writes.

Acceptance: `scale`/`tag`/accessor tests pass, the documented fallback behavior
is covered, and the full suite is green.

## Resolution

Implemented in `src/plone/namedfile/brain_scaling.py`:

- `_context_origin()`/`_resolved_origin()` for brained and already-woken
  contexts; `_object_view()` returns `None` when the fallback object is gone.
- `_is_valid_entry()` with type checks for download/width/height;
  `_match_dimensions()` for explicit dimension lookups; `_build_scale()`.
- `scale()` with the approved matrix:
  - metadata for present named scales, the original, exact dimensions, default
    mode, and `pre=True`;
  - fallback for missing configured scales, arbitrary dimensions, non-default
    modes, extra parameters, malformed metadata, and schema-less catalogs;
  - `scale` not in `available_sizes` -> `None` before any fallback;
  - debug logs with fieldname/scale/reason on every fallback.
- `tag()` delegates to `scale(..., pre=True)`, consumes `include_srcset`, and
  returns the scale tag or `None`.
- `getImageSize()` returns metadata dimensions, falls back for missing/corrupt
  dimensions, and returns `(0, 0)` for no image.
- `modified()` uses `brain.modified` and returns `0` for missing/invalid values.
- `Unauthorized` propagates; `getObject() is None` yields the empty-result
  contract.

Documented a newly discovered divergence in `SPEC.md` and `TEST-PLAN.md`: the
object view's no-dimension original uses the storage `image-0` UID, while the
metadata original uses the indexed `image-<width>` URL; parity compares against
explicit original dimensions.

Verification:

- `test_brain_images`: 66 tests, 0 failures.
- Full suite: 203 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

Review fixes: added fallback debug logging; type-checked malformed metadata;
moved the unknown-scale check before the parameter/mode fallback; made
`modified()` handle `Missing.Value`; added Unauthorized `getImageSize`,
scale-with-dimensions, `pre=True`, wrong-typed metadata, and missing-modified
tests; consolidated HIDPI test setup and missing-dimension fixtures; renamed
the shadowed `id`; refactored origin/dimension helpers.

Review accepted: the `_fallback_scale` argument clump mirrors the
`ImageScaling.scale` signature; extra `**parameters` must fall back because
metadata cannot honor them; `modified()` intentionally reads `brain.modified`
rather than the object's `_p_mtime`. The HiDPI `include_srcset=True` fallback
remains in I7.

No GitHub writes.
