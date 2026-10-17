---
id: I1
title: "Add the Plone test layer and fixture helpers"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: [D11]
---

## Question

Implement the test foundation described in `TEST-PLAN.md`.

Do:

1. In `src/plone/namedfile/testing.py`, add
   `NamedFilePloneLayer(defaultBases=(PLONE_FIXTURE,))`,
   `NAMEDFILE_PLONE_INTEGRATION`, and `NAMEDFILE_PLONE_FUNCTIONAL`.
2. Add `src/plone/namedfile/tests/brain_images_helpers.py` with:
   - content factories for an `Image` (200x200) and a 900x900 image;
   - a programmatic multi-field Dexterity type helper;
   - a fake `ICatalogBrain` for malformed/multi-entry/Unauthorized cases;
   - the `IContentListingObject(brain)` wrapper helper;
   - the DOM parity normalizer and `srcset`/`picture` comparison helpers;
   - strict and counting `AbstractCatalogBrain.getObject` /
     `_unrestrictedGetObject` instrumentation with a positive control;
   - stale/malformed metadata helpers.
3. Add a smoke test proving the layer starts, content can be cataloged, a
   brain is obtained, and the instrumentation records a real `getObject()`
   call.
4. Leave the full existing suite green.

Do not implement the brain view or its registrations yet. No GitHub writes.

Acceptance: `tox -e py312-plone62` is green, the new layer and helpers import,
and the positive-control instrumentation test passes.

## Resolution

Implemented:

- `NamedFilePloneLayer`, `NAMEDFILE_PLONE_INTEGRATION`, and
  `NAMEDFILE_PLONE_FUNCTIONAL` in `testing.py`, based on `PLONE_FIXTURE`.
- `tests/brain_images_helpers.py` with:
  - 200x200 and 900x900 image factories, multi-image type/item helpers;
  - a `FakeBrain` that records `Title`/`UID`/`modified`/`getURL`/`getPath`/
    `getObject` access and raises on unexpected wake-ups;
  - contentlisting wrapper, stale/malformed metadata, entry builders, and
    `first_image_entry` helpers;
  - strict and counting `AbstractCatalogBrain.getObject` instrumentation;
  - ordered `srcset`, recursive DOM parity, and scale comparator helpers.
- `tests/test_brain_images.py` with 9 smoke tests (layer, catalog brain,
  instrumentation positive control, fake brain access, wrapper, DOM/scale
  comparators, stale metadata, multi-image type).
- `.meta.toml`/`pyproject.toml` check-manifest ignore for `.imagesplan` so the
  tracked plan is not forced into the sdist.

Verification:

- `zope-testrunner ... -m 'test_brain_images'`: 9 tests, 0 failures.
- Full suite: 146 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

No brain view, registration, or production code was added. No GitHub writes.
