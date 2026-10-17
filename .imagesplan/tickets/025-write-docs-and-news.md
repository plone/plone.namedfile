---
id: I9
title: "Write docs, README section, news fragment, and packaging"
type: task
mode: AFK
status: closed
claimed_by: erral
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

## Resolution

Added:

- `docs/brain-images.rst`: overview, availability, public API, metadata-first
  behavior, fallback rules, field resolution, `srcset`, `picture`, HiDPI,
  security, documented divergences, non-goals, and related documentation.
- A README section with a named link to the new page.
- The docs page in `setup.py`'s `long_description` between `CHANGES.rst` and
  `usage.rst`.
- `news/brain-images.feature` with the approved wording.

Validation:

- `docutils` parses `docs/brain-images.rst` and `README.rst`; the only
  messages are Pygments-not-installed warnings.
- `uv build --sdist` succeeds; the sdist contains
  `docs/brain-images.rst` and excludes the `news/` fragment as intended.
- `uvx twine check` passes with the pre-existing
  `long_description_content_type` warning.
- Full suite: 258 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

Review fixes: stated the Plone 6.2 scope, documented the unknown/empty
`picture()` branches and field-resolution debug log, corrected `alt`/`title`
default notation, documented absolute/root-relative download passthrough, and
qualified picture preflight by registry width; rewrapped the README link.

Review accepted: the descriptive `news/brain-images.feature` name is required
because no GitHub issue is created (the ticket explicitly forbids one); the
README/docs/news summaries intentionally repeat the user-facing outcome; the
docs page is intentionally in `long_description`; long API definition-list
lines are not wrapped by RST tooling.

No `CHANGES.rst` edit, version bump, GitHub write, or release.
