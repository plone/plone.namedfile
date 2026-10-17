---
id: I9
title: "Write docs, README section, news fragment, and packaging"
type: task
mode: AFK
status: open
claimed_by: null
blocked_by: [D11, I4, I5, I6, I7]
---

## Question

Implement `SPEC.md` section 13.

Do:

1. Add `docs/brain-images.rst` covering:
   - the brain-aware view and its registrations;
   - plain-brain and contentlisting `getMultiAdapter` examples;
   - the public API and metadata-first/fallback contract;
   - field resolution;
   - the HiDPI table;
   - security caveats;
   - documented divergences;
   - non-goals and the Plone 6.2 scope.
2. Add a short README section linking to the docs with an absolute GitHub URL.
3. Include `docs/brain-images.rst` in `setup.py`'s `long_description` between
   `CHANGES.rst` and `usage.rst`.
4. Add `news/brain-images.feature` per the approved wording.
5. Do not edit `CHANGES.rst`, do not bump the version, and do not publish.
6. Validate the RST and packaging (sdist build and `twine check` if
   available).

No GitHub writes.

Acceptance: docs/news/long_description are present and valid, and the existing
suite remains green.
