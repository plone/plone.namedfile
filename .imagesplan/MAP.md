# Wayfinder map: Brain-aware `@@images`

## Destination

A feature-complete `@@images` view in `plone.namedfile` that works with catalog
brains and `plone.app.contentlisting` wrappers: the same method surface as the
object view (`scale`, `tag`, `srcset`, `picture`, `getImageSize`,
`available_sizes`, `modified`), metadata-first with explicit object fallback,
zero `getObject()` calls on the metadata path, fully tested and documented.
Delivered as local commits on a `brain-images` branch, with no GitHub writes;
the version bump is left to the release manager.

## Notes

- Repo: `plone.namedfile` 8.1.2-dev, Plone 6.2 only. Source precedent:
  `NavigationRootScaling` (`@@image_scale`) and `cs.srcset`'s `@@image_helper`;
  use them as inspiration, do not modify them.
- Brain metadata shape: `brain.image_scales[fieldname]` is a list of dicts with
  `filename`, `content-type`, `size`, `download`, `width`, `height`, and
  `scales` (name -> `download`/`width`/`height`). The original image's
  `download` is already a stable UID URL. Old-style HiDPI 2x/3x scales are
  absent.
- Skills: every decision ticket calls `grilling` + `domain-modeling`; research
  tickets call `research`; implementation follows `tdd` if available.
- Standing preferences: filesystem tracker only. **Never write to GitHub**
  (issues, comments, PRs, pushes) without an explicit order. Local branch and
  commits only; no push, PR, or release. Plone 6.2 only. `cs.srcset`,
  `NavigationRootScaling`, and `@@images` traversal on brains are out of scope.
- Execution is in scope: the specification is approved and implementation is
  carried by task tickets I1-I10. Each must keep the full suite green.
- Tracker conventions: see `README.md`; frontier via
  `python .imagesplan/frontier.py`.

## Decisions so far

- [Verify brain view registration and resolution](tickets/001-verify-brain-view-registration.md): register the brain-aware `images` page for `ICatalogBrain` and, conditionally, `IContentListingObject`; both coexist with the object page, and wrappers must be unwrapped via `getDataOrigin()`.
- [Map image_scales metadata lifecycle and staleness](tickets/002-map-image-scales-metadata-lifecycle.md): metadata is `PersistentMapping[field -> list[entry]]` or `Missing.Value`, written on reindex via `pre_scale`; UID URLs can 404 after clear or stale indexing; metadata reads never wake the object and contain no HiDPI information.
- [Assess metadata-only picture() feasibility](tickets/003-assess-metadata-only-picture.md): parity is conditional on every variant scale being present in metadata; scales wider than the original are omitted, so missing scales require object fallback or a documented non-parity mode.
- [Map test infrastructure and zero-wake-up instrumentation](tickets/004-map-test-infrastructure.md): use a package-local Plone sandbox layer, catalog real content, and patch `AbstractCatalogBrain.getObject`/`_unrestrictedGetObject` to prove zero wake-ups; baseline is 137 tests, 0 failures, 1 pre-existing skip in an unofficial local environment.
- [Prepare the local test environment and baseline](tickets/005-prepare-local-test-baseline.md): `.tox/py312-plone62` on Python 3.12.3 with the Plone 6.2-dev constraints is green (137 tests, 0 failures, 1 pre-existing skip); single-module runs work with `-m`.
- [Design the brain-aware view class and registration](tickets/006-design-brain-view-class-and-registration.md): `BrainImageScaling(ImageScaling)` in `brain_scaling.py`; metadata origin via `getDataOrigin()` + `ICatalogBrain.providedBy()`; fallback through the real object's `@@images`; `images` pages for `ICatalogBrain` and conditional `IContentListingObject`; traversal refused on brains.
- [Design the metadata-backed scale object](tickets/007-design-metadata-backed-scale-object.md): `BrainImageScale(ImageScale)` with `data=None`; metadata constructor, origin-based URL helper, and overrides for `tag`, `title`, `srcset_attribute`, access checks, and data-serving; no storage UID and no bytes on the metadata path.
- [Define the metadata-first fallback matrix](tickets/008-define-fallback-matrix.md): schema-aware no-metadata handling; metadata for present scales/original/exact dimensions/default mode, fallback for missing configured scales, arbitrary dimensions, non-default modes, and HiDPI; `getObject() is None` yields empty results, `Unauthorized` propagates, stale URLs are documented, and fallbacks log at debug level.
- [Specify field resolution and multi-image metadata](tickets/009-specify-field-resolution-and-multi-image.md): one resolver for all methods; omitted `fieldname` works only when exactly one image field exists; explicit fieldname otherwise; use the first entry of a multi-entry list; no primary-field lookup and no wake; ambiguity returns `None`/`(0, 0)` with a debug log.
- [Specify srcset parity from metadata](tickets/010-specify-srcset-parity.md): mirror the object ordering, original inclusion, `scale_in_src`, and attributes; skip scales missing from metadata (documented divergence); fall back only when the selected `scale_in_src` is missing; URLs come from metadata `download`.
- [Design metadata-backed picture()](tickets/011-design-metadata-backed-picture.md): add a resolver hook to `Img2PictureTag`; preflight every variant-required scale and fall back the whole call if any is missing; descriptors from `IAvailableSizes`, `<img>` dimensions from metadata, zero wake-ups on the fast path.
- [Specify the HiDPI include_srcset API](tickets/012-specify-hidpi-include-srcset.md): add `include_srcset` to brain `scale()`/`tag()`; `None`/`False` omit, `True` without HiDPI is a no-op, `True` with HiDPI falls back to the object; `srcset()`/`picture()` remain HiDPI-free and the registry check never wakes.
- [Specify security and unauthorized behavior](tickets/013-specify-security-and-unauthorized.md): no extra permission check on metadata (same exposure as `image_scales`); URL serving protects bytes; field-level permissions are not enforced on the metadata path and must use the object view; `Unauthorized` propagates, `getObject() is None` yields empty results, and permission failures are not logged at info level.
- [Design the test plan and parity harness](tickets/014-design-test-plan-and-parity-harness.md): full plan in `.imagesplan/TEST-PLAN.md`; package-local Plone integration/functional layers; real-content plus fake-brain fixtures; strict zero-wake patches with a positive control; DOM-based parity; commands for py312 and the CI matrix; zero-wake count as the performance guard.
- [Specify docs, changelog, and release packaging](tickets/015-specify-docs-changelog-release.md): new `docs/brain-images.rst` included in `long_description` plus a README link; `news/brain-images.feature` and no manual `CHANGES.rst` edit; leave the version at `8.1.2.dev0` for the release manager; no release or push.
- [Approve the specification](tickets/016-approve-specification.md): `SPEC.md` and `TEST-PLAN.md` approved; implementation graduated into task tickets I1-I10; version unchanged, no GitHub writes.
- [Add the Plone test layer and fixture helpers](tickets/017-add-test-layer-and-fixtures.md): package-local Plone integration/functional layers, real-content and fake-brain fixtures, stale/malformed helpers, strict/counting `getObject` instrumentation, ordered DOM/scale comparators, and 9 smoke tests; full suite 146 green, lint green.
- [Add the brain view skeleton, registration, and resolvers](tickets/018-add-view-skeleton-registration-and-resolvers.md): `BrainImageScaling(ImageScaling)` in `brain_scaling.py`; `images` pages for `ICatalogBrain` and conditional `IContentListingObject`; metadata-origin, object-fallback, schema, field, and title resolvers; traversal refusal; 25 brain tests and 162-test full suite green.
- [Implement BrainImageScale and the metadata URL helper](tickets/019-implement-brain-image-scale.md): `BrainImageScale(ImageScale)` with `data=None`, metadata constructor, URL join/pass-through rules, `tag`/`title`/`srcset_attribute`, access no-op, and data-serving refusal; 39 brain tests and 176-test full suite green.
- [Implement scale, tag, accessors, and fallback delegation](tickets/020-implement-scale-tag-and-fallback.md): metadata-first `scale`/`tag`/`getImageSize`/`modified`, the full fallback matrix with debug logs, malformed-metadata guards, `Unauthorized`/missing-object behavior, and documented original-URL divergence; 66 brain tests and 203-test full suite green.
- [Implement srcset() from metadata](tickets/021-implement-srcset.md): object-order `srcset` from metadata, original inclusion, `scale_in_src` selection, skip-missing divergence, malformed-nested fallback, full attribute parity, and zero wake-ups; 82 brain tests and 219-test full suite green.
- [Add the picture resolver hook and implement picture()](tickets/022-implement-picture.md): optional `Img2PictureTag` scale resolver, metadata preflight with whole-call fallback, variant/empty handling, object-compatible attributes, and zero `uuidToObject`/wake-ups on the fast path; 95 brain tests and 232-test full suite green.
- [Implement HiDPI include_srcset behavior](tickets/023-implement-hidpi-include-srcset.md): explicit `include_srcset=True` falls back to the object only when HiDPI is configured; defaults and other fallbacks stay HiDPI-free; registry-driven and zero-wake tests; 106 brain tests and 243-test full suite green.

## Not yet specified

None. The specification is approved and implementation is ticketed as I1-I10.

## Out of scope

- Updating or replacing `cs.srcset`, `@@image_helper`, or `@@images-srcset` —
  separate effort; the new API may inspire it later.
- Delegating or deprecating `NavigationRootScaling` (`@@image_scale`) — separate
  cleanup.
- URL traversal or serving of `@@images` on brains (`publishTraverse`,
  `/@@images/...`) — brains are not URL-addressable; scale URLs resolve on the
  real object.
- Editing or uploading image fields through a brain view.
- Plone 6.1 or earlier support.
- GitHub issues, comments, PRs, pushes, and releases.
- A context-bound convenience helper (an `@@image_helper`-style view) —
  developers use `getMultiAdapter((item, request), name="images")`.
