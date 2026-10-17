---
id: T1
title: "Prepare the local test environment and baseline"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: []
---

## Question

Prepare this checkout for implementation and record the baseline.

Do:

1. Create or activate a local environment (tox or uv) for Plone 6.2 and
   Python 3.12 if one is not already available.
2. Run the existing `plone.namedfile` test suite, or at least the scaling tests,
   and record the exact command, package versions, pass/fail counts, and any
   pre-existing failures.
3. Verify that a single test module can be run directly (the command later
   sessions will use).
4. Record the commands and environment facts in this ticket's `## Resolution`.

Do not change package code. Do not write to GitHub.

## Resolution

Environment created with the project's pinned tox environment:

```sh
tox -e py312-plone62
```

- Venv: `.tox/py312-plone62`, Python 3.12.3.
- Constraints: `https://dist.plone.org/release/6.2-dev/constraints.txt`.
- Key versions: `plone.namedfile` 8.1.2.dev0 (editable), `Products.CMFPlone`
  6.2.2, `Zope` 6.2, `plone.scale` 5.1.0, `plone.app.testing` 8.0.2,
  `plone.app.contenttypes` 5.0.1, `plone.app.contentlisting` 4.0.0,
  `plone.dexterity` 4.0.0, `plone.base` 4.0.2, `zope.testrunner` 8.3.
- Full suite: **137 tests, 0 failures, 0 errors, 1 skipped** (0.525s). The skip
  is pre-existing; the only warnings are the existing `getAvailableSizes`
  deprecation and `cgi` import deprecation.
- Single-module command works directly:

```sh
.tox/py312-plone62/bin/zope-testrunner \
  --test-path=src -s plone.namedfile -m 'test_scaling$'
```

Result: **54 tests, 0 failures, 0 errors, 0 skipped** (0.341s). Use `-s` for the
package and `-m` for the module filter; future brain tests can use
`-m 'test_brain_images'`.

No package code was changed and nothing was written to GitHub. The environment
is ready for the implementation sessions.
