---
id: D9
title: "Design the test plan and parity harness"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R4, D1, D2, D3, D5, D6, D7, D8]
---

## Question

Design the test plan and parity harness for the brain-aware view.

Decide:

- Test layers and fixtures: plain `ICatalogBrain`, `IContentListingObject`,
  multiple image fields, relation lists, and empty/missing images.
- Brain-versus-object HTML parity for `scale()`, `tag()`, `srcset()`, and
  `picture()`.
- Zero-wake-up assertions on the metadata path, including how to instrument
  `getObject()`.
- Missing, malformed, stale, and cleared-scale metadata.
- HiDPI configured versus not configured.
- Security cases.
- Regression tests proving the existing object-backed `@@images` is unchanged.
- Plone 6.2-only matrix and exact commands.

Inputs: "Map test infrastructure and zero-wake-up instrumentation" and the
fallback, `srcset`, `picture`, HiDPI, and security decisions.

Output: the outline of `.imagesplan/TEST-PLAN.md` and the commands to run.

## Resolution

The full plan is written to [`.imagesplan/TEST-PLAN.md`](../TEST-PLAN.md). It
is the artifact the specification-approval ticket will review.

Summary of the decisions:

- **Layers**: add `NamedFilePloneLayer` on `PLONE_FIXTURE`, plus
  `NAMEDFILE_PLONE_INTEGRATION` and `NAMEDFILE_PLONE_FUNCTIONAL`, in
  `testing.py`. Use the integration layer for parity, fallbacks, field
  resolution, security contracts, and zero-wake assertions; use the functional
  layer only for browser/URL serving.
- **Modules**: `tests/test_brain_images.py`,
  `tests/test_brain_images_functional.py`, and
  `tests/brain_images_helpers.py` for shared fixtures, normalizers, and
  instrumentation.
- **Fixtures**: real `Image`/`News Item` content for common cases
  (`tests/image.png` 200x200, `tests/900.jpg` 900x900), a programmatic
  Dexterity type for multiple image fields, and a fake `ICatalogBrain` for
  malformed, multi-entry, `Missing.Value`, and `Unauthorized` states. Use
  `IImageScaleStorage.clear()` and `reindexObject(update_metadata=0)` for
  staleness.
- **Zero-wake harness**: strict `AssertionError` patches on
  `AbstractCatalogBrain.getObject`/`_unrestrictedGetObject`, plus a counting
  positive-control test; never patch traversal or acquisition.
- **Parity harness**: build object, brain, and wrapper views with the same
  request; parse fragments and compare tag names/attribute dictionaries;
  assert exact URLs/UIDs when metadata is in sync; compare `srcset` as ordered
  URL/descriptor pairs; compare all `picture` source and img attributes; do not
  compare `.data`.
- **Cases**: registration/lookup, `scale`/`tag`, `srcset`, `picture`, field
  resolution, fallback matrix, HiDPI, security, and object-view regression.
- **Commands**: `tox -e py312-plone62` plus the new modules via
  `zope-testrunner -s plone.namedfile -m 'test_brain_images'` and
  `-m 'test_brain_images_functional'`; CI uses the existing py310-py314 Plone
  6.2 matrix.
- **Performance guard**: zero `getObject()`/`_unrestrictedGetObject()` calls on
  metadata paths; no timing thresholds.
- **Documented divergences**: missing-scale `srcset` skip, default HiDPI
  omission, field-permission limitation, and stale URL 404s.
