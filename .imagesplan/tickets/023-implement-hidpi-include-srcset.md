---
id: I7
title: "Implement HiDPI include_srcset behavior"
type: task
mode: AFK
status: open
claimed_by: null
blocked_by: [D11, I4]
---

## Question

Implement `SPEC.md` section 10.

Do:

1. Add the named `include_srcset` keyword to brain `scale()` and `tag()`.
2. Implement the behavior table:
   - `None`/`False` -> metadata, no HiDPI, no wake;
   - `True` with no HiDPI configured -> metadata, no HiDPI, no wake;
   - `True` with HiDPI configured -> fall back to the object-backed
     `scale()`/`tag()` and return its HiDPI output.
3. Use `getHighPixelDensityScales()` for the registry check.
4. Ensure `tag()` consumes the keyword and never renders it.
5. Leave `srcset()` and `picture()` free of `include_srcset`.
6. Add tests for configured/unconfigured HiDPI, zero-wake defaults, the
   explicit fallback, and the HTML-attribute guard.

No GitHub writes.

Acceptance: HiDPI tests pass and the full suite is green.
