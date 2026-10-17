---
id: I6
title: "Add the picture resolver hook and implement picture()"
type: task
mode: AFK
status: open
claimed_by: null
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
