---
id: I6
title: "Add the picture resolver hook and implement picture()"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: [D11, I4]
---

## Question

Implement `SPEC.md` section 9.4.

Do:

1. In `src/plone/namedfile/picture.py`, add the optional
   `scale_resolver` parameter to
   `Img2PictureTag.create_picture_tag()`. When it is `None`, preserve the
   existing object-backed behavior exactly. When provided, it replaces
   `uuidToObject()` and `unrestrictedTraverse("@@images")`.
2. Implement `BrainImageScaling.picture()`:
   - variant lookup and unknown-variant `tag()` delegation;
   - target scale from `sourceset[-1]["scale"]`;
   - preflight all required scales (target plus `additionalScales`, or all
     allowed except target), requiring metadata and registry widths;
   - whole-call fallback on any missing required scale;
   - the exact attribute rules (`class`, `src`, width/height, title, alt);
   - `resolver(scale_name)` returning metadata URL/actual dimensions;
   - empty `sourceset` -> warning + `None`;
   - zero `uuidToObject()` / `getObject()` / traversal on the fast path.
3. Add tests proving the object path is unchanged, picture parity, preflight
   fallback, attribute behavior, and zero wake-ups.

No GitHub writes.

Acceptance: `picture` and existing `picture.py` tests pass, and the full suite
is green.

## Resolution

Implemented:

- `src/plone/namedfile/picture.py`: optional `scale_resolver` on
  `Img2PictureTag.create_picture_tag()`. With `None`, the object path is
  unchanged; with a resolver, it replaces `uuidToObject()` and
  `unrestrictedTraverse("@@images")`, and a missing target resolution falls
  back to the provided `src` instead of guessing a URL.
- `BrainImageScaling.picture()`:
  - resolves the field/entry first, so a no-image brain returns `None` before
    variant handling;
  - unknown variant -> warning + metadata `tag()`;
  - empty/`{}` variant or empty sourceset -> warning + `None`;
  - preflights the target and required additional scales (registry-width
    scales only), falling back the whole call when metadata is missing;
  - builds the object-compatible attributes (`class`, `src`, width/height,
    normalized title, truthy alt);
  - uses a metadata resolver for every source and the target image;
  - falls back through the object view with the originally requested
    fieldname.
- Zero `uuidToObject()`, `getObject()`, or `@@images` traversal on the fast
  path; verified with a `uuidToObject` side-effect and strict wake checks.

Tests cover parity, media/sizes, caller attributes, unknown variants, empty
variants/sourcesets, omitted `additionalScales`, unknown additional scales,
missing target/additional scales, malformed metadata, Unauthorized fallback,
no-image brains, schema-less catalogs, wrappers, and zero wake-ups.

Verification:

- `test_brain_images`: 95 tests, 0 failures.
- Full suite: 232 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

Review fixes: resolve metadata before variant handling; distinguish empty `{}`
variants from unknown ones; use the provided target `src` when a resolver
returns `None`; preserve the requested fieldname in fallbacks; added the
missing tests for media, omitted `additionalScales`, Unauthorized, malformed
nested scales, and no-image unknown variants; reused the `picture_without_uuid`
helper; renamed the resolver closure.

Review accepted: the `picture()` duplication mirrors the approved design;
fallback option groups keep call sites explicit; the resolver payload is a
small, documented module-boundary contract; the module alias is required so
tests can patch registry lookups; an unregistered target follows the builder's
object-parity skip behavior; malformed non-target scales fall back per SPEC 8.

No GitHub writes.
