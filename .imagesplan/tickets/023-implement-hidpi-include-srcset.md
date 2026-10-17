---
id: I7
title: "Implement HiDPI include_srcset behavior"
type: task
mode: AFK
status: closed
claimed_by: erral
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

## Resolution

Implemented in `BrainImageScaling`:

- `include_srcset=True` with configured HiDPI now falls back through the
  object-backed `scale()`/`tag()`; the fallback passes the flag explicitly.
- `None`/`False`, unknown scale names, and no-image cases stay on the metadata
  path with no HiDPI and no wake-ups.
- `True` without configured HiDPI stays on metadata and is a no-op.
- `_fallback_scale()` now passes `include_srcset=False` unless the caller
  explicitly passed `True`, so a fallback caused by another reason cannot
  re-enable HiDPI implicitly (`pre=True` + `None` in the object path).
- `tag()` consumes the keyword; it is never rendered as an HTML attribute.
- `srcset()` and `picture()` have no `include_srcset` parameter.

Tests cover default/False omission, `pre=True` omission, `True` without HiDPI,
explicit scale/tag fallback with parity and one wake-up, the default fallback
not re-enabling HiDPI, registry-driven HiDPI configuration, unknown/no-image
edges, and the absence of the parameter on `srcset`/`picture`.

Verification:

- `test_brain_images`: 106 tests, 0 failures.
- Full suite: 243 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

Review fixes: normalized the fallback flag to prevent implicit HiDPI; added a
registry-backed HiDPI test; added the `srcset`/`picture` signature guard; used
one class-level HiDPI test helper and removed duplicate setup.

Review accepted: the extra fallback reason arm mirrors the existing guard
cascade; `is True` is deliberate because the public contract is boolean; the
unknown/no-image HiDPI tests are useful fallback-matrix edges.

No GitHub writes.
