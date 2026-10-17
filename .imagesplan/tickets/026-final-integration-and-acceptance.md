---
id: I10
title: "Final integration, local branch, and acceptance"
type: task
mode: AFK
status: open
claimed_by: null
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
