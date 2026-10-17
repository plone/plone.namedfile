---
id: I4
title: "Implement scale, tag, accessors, and fallback delegation"
type: task
mode: AFK
status: open
claimed_by: null
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
