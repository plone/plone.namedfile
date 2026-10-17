---
id: I2
title: "Add the brain view skeleton, registration, and resolvers"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: [D11, I1]
---

## Question

Implement the structural parts of `SPEC.md` sections 5.1, 5.2, 5.3, 6, and 7.

Do:

1. Create `src/plone/namedfile/brain_scaling.py` with
   `BrainImageScaling(ImageScaling)` and helpers:
   - `_metadata_origin()` using `getDataOrigin()` and
     `ICatalogBrain.providedBy()` without waking;
   - `_object_view(origin)` using `getObject()` only for a brain origin;
   - the schema-aware `image_scales` check (no wake);
   - `_resolve_metadata(fieldname)` implementing the field-resolution rules,
     including the first-entry rule and debug logs;
   - a normalized `_title()` helper.
2. Create `brain_scaling.zcml` with the two `images` pages and include it from
   `configure.zcml`. Leave `scaling.zcml` untouched.
3. Override `publishTraverse`, `traverse`, and `browserDefault` to refuse
   serving on brains.
4. Keep the module import-safe without `plone.app.contentlisting`.
5. Add tests proving a plain brain and a catalog wrapper resolve to
   `BrainImageScaling`, a real content object still resolves to
   `ImageScaling`, and the field/schema resolvers behave as specified.

Method behavior (`scale`, `tag`, `srcset`, `picture`) is out of scope here.
No GitHub writes.

Acceptance: registration/context/field-resolution tests pass, the existing
object-backed view is unchanged, and the full suite is green.

## Resolution

Implemented:

- `src/plone/namedfile/brain_scaling.py` with `BrainImageScaling(ImageScaling)`:
  - `_title()` normalization helper;
  - `_metadata_origin()` using `getDataOrigin()` plus
    `ICatalogBrain.providedBy()`, without waking;
  - `_object_view()` that wakes only a brain origin and resolves the real
    object's `@@images`;
  - `_supports_image_scales_metadata` (schema check, no wake);
  - `_resolve_metadata()` with explicit/omitted field rules, first-entry
    handling, empty-entry protection, and debug logs for no metadata, ambiguous
    fields, and multiple entries;
  - `publishTraverse`/`traverse`/`browserDefault` refusal.
- `src/plone/namedfile/brain_scaling.zcml` with the `ICatalogBrain` page and the
  conditional `IContentListingObject` page, included from `configure.zcml`.
  `scaling.zcml` is untouched.
- Tests for plain brain, catalog wrapper, real content, real-object wrapper,
  already-woken wrapper, schema checks, title normalization, object delegation,
  field resolution, empty/multiple entries, and traversal refusal.

Verification:

- `test_brain_images`: 25 tests, 0 failures.
- Full suite: 162 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

The metadata-aware `scale`/`tag`/`srcset`/`picture` methods are still inherited
from `ImageScaling`; I4-I7 implement them. No GitHub writes.
