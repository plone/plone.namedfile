---
id: R4
title: "Map test infrastructure and zero-wake-up instrumentation"
type: research
mode: AFK
status: closed
claimed_by: research-agent-R4
blocked_by: []
---

## Question

Map the existing test infrastructure needed to prove parity and zero wake-ups.

Investigate:

- `src/plone/namedfile/testing.py`, `tests/test_scaling.py`,
  `tests/test_scaling_functional.py`, and fixtures in `tests/`.
- How to create content with named image fields, catalog and reindex it, and
  obtain a brain with `image_scales`; how to clear or invalidate scales; how to
  test missing, malformed, and stale metadata.
- How to assert that `getObject()` is never called (monkeypatch, wrapper, or
  instrumentation) without breaking acquisition.
- The functional/browser test layer, how scale URLs are served, and how to
  compare brain and object HTML.
- Commands to run the suite (tox environments, Plone 6.2 constraints), and the
  current baseline if cheap to check. Do not change package code.

Deliverable: a test recipe, layer choices, helper snippets, and exact commands
for the test plan and implementation sessions.

## Resolution

Use a package-local `PloneSandboxLayer` based on `plone.app.testing.PLONE_FIXTURE`
for brain tests; the existing `NamedFileTestLayer` has no Plone site or catalog.
`PLONE_FIXTURE` applies `plone.app.contenttypes:default`, so `Image`/`News Item`
and the `image_scales` catalog column are available. Create an image item, assign
`NamedImage`, call `reindexObject()`, and get the brain from
`portal_catalog(UID=...)`. Metadata is a `PersistentMapping` keyed by fieldname;
`download` values are relative scale paths. Missing images yield
`Missing.Value`; stale metadata can be produced with `storage.clear()` or
`reindexObject(update_metadata=0)`; malformed payloads can be injected by
shadowing `brain.image_scales`. Instrument
`Products.ZCatalog.CatalogBrains.AbstractCatalogBrain.getObject` and
`_unrestrictedGetObject` with counting/raising wrappers, always including a
positive-control test; `CatalogContentListingObject` delegates to the brain and
`getDataOrigin()` does not wake. Build the wrapper with
`IContentListingObject(brain)` (single adapter). Parity is best done in the
integration layer with normalized DOM comparison and exact scale UIDs where
possible; browser tests only prove served URLs. Full local baseline:
137 tests, 0 failures, 1 pre-existing skip. See
[R4-test-infrastructure.md](../research/R4-test-infrastructure.md).
