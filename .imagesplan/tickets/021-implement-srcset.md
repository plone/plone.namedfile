---
id: I5
title: "Implement srcset() from metadata"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: [D11, I4]
---

## Question

Implement `SPEC.md` section 9.3.

Do:

1. Implement `srcset()` with:
   - original inclusion only when its width is not an available width;
   - registry-order iteration over `available_sizes`;
   - only configured widths `<= original_width`;
   - metadata URLs and actual metadata widths for `w` descriptors;
   - skip-missing behavior for configured scales absent from metadata, with a
     debug log and no whole-call fallback;
   - `scale_in_src` selection and fallback when the selected scale is missing;
   - the exact object attribute behavior (`title`/`alt` defaults, `sizes`,
     `css_class`, kwargs, `src`, `width`, `height`).
2. Use the metadata URL helper and the normalized title helper.
3. Add parity tests, the skip-missing divergence test, the selected
   `scale_in_src` fallback test, and zero-wake tests.

No GitHub writes.

Acceptance: `srcset` parity/divergence tests pass and the full suite is green.

## Resolution

Implemented `BrainImageScaling.srcset()` in `src/plone/namedfile/brain_scaling.py`:

- original inclusion only when its width is not an available width;
- registry-order iteration over `available_sizes`, widths `<= original_width`;
- metadata URLs with actual metadata widths as `w` descriptors;
- missing configured scales are skipped with a debug log (no fallback);
  malformed nested scale entries fall back;
- `scale_in_src` selection mirrors the object view, including the first
  available width when the requested name is unknown; a missing selected scale
  falls back;
- object attribute behavior: normalized `Title`/`alt` defaults, `sizes`,
  `class`, kwargs, caller width/height, `src`, `srcset`;
- schema-less catalogs, malformed originals, zero dimensions, and missing
  selected scales fall back with debug logs;
- no image returns `None` without waking.

Tests cover 900px and 200px parity, original inclusion/absence, attributes,
caller dimensions, falsy title, skip-missing (descriptor, length, debug log),
selected-scale fallback parity, default `huge` fallback, unknown
`scale_in_src`, no image, schema-less catalogs, malformed/zero metadata,
malformed nested scales, wrappers, and zero wake-ups.

Verification:

- `test_brain_images`: 82 tests, 0 failures.
- Full suite: 219 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

Review fixes: distinguished missing (skip) from malformed (fallback) nested
scales; added the skip debug assertion; tested caller dimensions, falsy title,
duplicate-original absence, shorter skip output, and fallback parity; added a
fallback-assertion helper; renamed the small-image test; parameterized the
field in the metadata fixture.

Review accepted: the `_fallback_srcset` argument clump mirrors the view
signature; the srcset logic duplicates `ImageScaling.srcset` by design; raw
metadata dict access is the catalog contract; fallback-matrix tests are
additional SPEC F coverage.

No GitHub writes.
