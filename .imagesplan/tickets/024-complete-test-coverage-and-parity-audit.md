---
id: I8
title: "Complete cross-cutting test coverage and parity audit"
type: task
mode: AFK
status: open
claimed_by: null
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
