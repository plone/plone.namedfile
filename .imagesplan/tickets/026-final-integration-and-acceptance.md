---
id: I10
title: "Final integration, local branch, and acceptance"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: [D11, I8, I9]
---

## Question

Finish the effort and verify the acceptance criteria in `SPEC.md` section 17.

Do:

1. Run the full suite with the pinned environment:
   `tox -e py312-plone62`.
2. Run lint (`tox -e lint` or the repository's pre-commit equivalent) if the
   environment is available.
3. Build the sdist and run `twine check` if available; verify the long
   description includes the new docs.
4. Walk the acceptance criteria:
   - brain and wrapper lookups resolve correctly; real content is unchanged;
   - `scale`/`tag`/`srcset`/`picture` parity and documented divergences;
   - zero wake-ups on metadata paths;
   - tests cover the fallback matrix, field resolution, HiDPI, security, and
     stale/malformed metadata;
   - docs/news/long_description present;
   - no version bump, no GitHub writes.
5. Create or use the local `brain-images` branch and commit the work locally.
   Do not push, open a PR, create issues, or release.
6. Record the commands, versions, test counts, branch name, and commit hashes
   in `## Resolution`.

If any acceptance criterion fails, keep the ticket open and report the
blocker instead of claiming completion.

Acceptance: every criterion passes, the full suite is green, and the work is
committed on the local `brain-images` branch.

## Resolution

Final validation was run on the local `brain-images` branch.

### Environment

- Python 3.12.3
- `plone.namedfile` 8.1.2.dev0
- `Products.CMFPlone` 6.2.2
- Zope 6.2
- `plone.scale` 5.1.0
- `plone.app.testing` 8.0.2
- `zope.testrunner` 8.3

### Commands and results

- `tox -e py312-plone62`: **258 tests, 0 failures, 0 errors, 1 skipped**
  (the skip is pre-existing).
- `tox -e lint`: all hooks pass.
- `uv build --sdist`: succeeds; the sdist contains `docs/brain-images.rst`
  and excludes the `news/` fragment as intended.
- `uvx twine check ...tar.gz`: **PASSED with warnings**, only the pre-existing
  `long_description_content_type` warning.

### Acceptance checklist

- ✅ Plain brains and catalog contentlisting wrappers resolve to
  `BrainImageScaling`; real content still resolves to `ImageScaling`.
- ✅ `scale`, `tag`, `srcset`, and `picture` have object parity for in-sync
  metadata, with the documented divergences tested.
- ✅ Metadata paths make zero `getObject()`/`_unrestrictedGetObject()` calls.
- ✅ The fallback matrix, field resolution, HiDPI, security, stale metadata,
  malformed metadata, wrappers, and functional serving are covered.
- ✅ The existing suite and resolver-less `picture.py` path are green.
- ✅ `docs/brain-images.rst`, the README link, the `long_description`
  inclusion, and `news/brain-images.feature` are present.
- ✅ `setup.py` remains at `8.1.2.dev0`; no version bump.
- ✅ No push, PR, issue, GitHub release, or PyPI upload was made.

### Branch and commits

`brain-images` was created at the current main tip (`5637470`) and contains
the complete effort:

- `8c9edfa` — test infrastructure
- `d918e2f` — view registration and resolvers
- `e45919f` — `BrainImageScale`
- `3661406` — scale/tag/accessors
- `6618b33` — `srcset`
- `eb375de` — `picture`
- `e3e7b3f` — HiDPI
- `834c627` — coverage audit
- `5637470` — docs/news/packaging
- this closure commit

`main` was used for the per-ticket commits before the final branch was created;
it remains at `5637470`. `brain-images` is the effort branch and carries the
final plan-closure commit. Nothing was pushed.
