---
id: I5
title: "Implement srcset() from metadata"
type: task
mode: AFK
status: open
claimed_by: null
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
