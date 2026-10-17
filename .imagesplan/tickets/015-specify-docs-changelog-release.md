---
id: D10
title: "Specify docs, changelog, and release packaging"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [D1, D3, D7]
---

## Question

Specify the documentation, changelog, and release packaging for the feature.

Decide:

- Where the docs live: a page under `docs/`, a README section, or both; RST or
  Markdown.
- Examples for a plain brain and a contentlisting item, using
  `getMultiAdapter((item, request), name="images")`.
- The explicit non-goals: no URL traversal on brains, no object wake-up on the
  metadata path, HiDPI opt-in, Plone 6.2 only.
- `CHANGES.rst` entry versus `news/` fragment (or both).
- The 8.2.0 minor version bump and whether `setup.py`/`CHANGES.rst` are updated
  as part of the implementation.
- No PyPI or GitHub release.

Inputs: the view, fallback, and HiDPI decisions.

Output: the file list and a documentation outline.

## Resolution

### Documentation

Add a dedicated RST page at `docs/brain-images.rst`, include it in
`long_description` (between `CHANGES.rst` and `src/plone/namedfile/usage.rst`),
and add a short README section linking to it.

The README link must be absolute (for example
`https://github.com/plone/plone.namedfile/blob/main/docs/brain-images.rst`)
because relative links do not resolve on PyPI.

The page covers:

- what the brain-aware `@@images` view is and which interfaces it serves
  (`ICatalogBrain`, `IContentListingObject`);
- plain-brain and contentlisting examples using
  `getMultiAdapter((item, request), name="images")`;
- the public API (`scale`, `tag`, `srcset`, `picture`, `getImageSize`,
  `available_sizes`, `modified`);
- the metadata-first/fallback contract and the zero-wake guarantee;
- field-resolution rules: one field may be inferred, explicit `fieldname`
  otherwise, first entry for multi-entry lists;
- the HiDPI `include_srcset` behavior table;
- security caveats: metadata is catalog data, URL serving enforces `View`,
  field-level permissions are not enforced on the metadata path;
- documented divergences: `srcset` skip-missing, default HiDPI omission, stale
  URLs can 404;
- non-goals: no URL traversal/serving on brains, no editing, no multi-image
  API, Plone 6.2 only;
- a note that `NavigationRootScaling`/`@@image_scale` and `cs.srcset` are
  unchanged and separate.

### Changelog

Add `news/brain-images.feature` describing the new public API and the
metadata-first behavior. Do **not** edit `CHANGES.rst`; towncrier renders it at
release time. No GitHub issue is created for the fragment.

Suggested fragment content:

```text
Add a brain-aware ``@@images`` view for catalog brains and contentlisting
objects. It exposes the same ``scale``, ``tag``, ``srcset``, ``picture``, and
``getImageSize`` API, answers from ``image_scales`` catalog metadata first, and
falls back to the real object only when metadata cannot answer. The metadata
path performs no ``getObject()`` calls, supports an explicit HiDPI fallback,
and documents the field-resolution and security caveats.
```

### Version and release

- Leave `setup.py` at `8.1.2.dev0`. Do not bump the version in this effort.
- The feature is a new public API, so the release manager can choose the next
  minor (for example 8.2.0) when releasing; the news fragment is the input.
- No PyPI upload, GitHub release, push, or PR. Implementation stays on the local
  `brain-images` branch.

### Packaging

- `docs/` is already grafted into the sdist; no `MANIFEST.in` change is needed.
- Update `setup.py`'s `long_description` to read the new docs page.
- Verify the long description and sdist build with the existing packaging
  commands (for example `python -m build --sdist` and `twine check` if
  available), without publishing.
