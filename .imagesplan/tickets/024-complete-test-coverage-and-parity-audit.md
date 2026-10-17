---
id: I8
title: "Complete cross-cutting test coverage and parity audit"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: [D11, I5, I6, I7]
---

## Question

Audit the implementation against `TEST-PLAN.md` and fill every remaining gap.

Do:

1. Map every case in `TEST-PLAN.md` (sections A-I) to a test. Add the missing:
   - multi-field content and omitted-fieldname ambiguity;
   - multiple entries per field (first-entry rule);
   - contentlisting wrapper parity and already-woken origin;
   - malformed, stale, and cleared metadata;
   - catalog without `image_scales` (simulated);
   - `getObject() is None` and `Unauthorized` from every affected method;
   - field-permission divergence and functional URL denial;
   - HiDPI configured/unconfigured cases;
   - object-backed regression tests and the resolver-less `picture.py` path;
   - the `getObject()` positive control.
2. Keep parity assertions DOM-based with exact URLs/UIDs when metadata is in
   sync; assert the documented divergences explicitly.
3. Run the full suite and fix any bug the new tests expose. Record any spec
   mismatch instead of silently changing behavior.
4. Update `TEST-PLAN.md` only if a case needs clarification.

No GitHub writes.

Acceptance: every `TEST-PLAN.md` case has a test, the full suite is green, and
no metadata-path test calls `getObject()`.

## Resolution

Added the missing TEST-PLAN coverage:

- New `test_brain_images_functional.py`:
  - a brain-generated scale URL serves the expected image bytes;
  - a stale metadata URL returns 404 after scale storage is cleared;
  - anonymous access to a private image does not return image bytes.
- New cross-cutting integration tests:
  - multi-field `scale`/`tag`/`srcset`/`picture` ambiguity and debug logging;
  - missing-field `getImageSize`;
  - `getObject() is None` for `tag`/`srcset`/`picture` and `modified` -> `0`;
  - `Unauthorized` from `tag` and `srcset`, with no identity in debug logs;
  - schema-less `getImageSize`/`modified` fallback;
  - 900px named-scale parity;
  - arbitrary-dimension fallback parity;
  - stale metadata still renders;
  - field-permission divergence: metadata dimensions render while the object
    guard raises `Unauthorized`;
  - resolver-less `Img2PictureTag` object path.

Review fixes: added the missing `srcset`/`picture` ambiguity and modified-zero
cases; added the identity-log check; added the resolver-less picture regression;
replaced the exact fallback wake count with a lower bound; strengthened the
anonymous denial assertion; asserted the object guard raises; named the
unauthorized fixture; renamed the audit class.

Verification:

- `test_brain_images` modules: 121 tests, 0 failures.
- Full suite: 258 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

No production behavior changed in this ticket. No GitHub writes.
