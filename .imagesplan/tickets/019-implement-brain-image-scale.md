---
id: I3
title: "Implement BrainImageScale and the metadata URL helper"
type: task
mode: AFK
status: closed
claimed_by: erral
blocked_by: [D11, I1]
---

## Question

Implement `SPEC.md` section 5.5.

Do:

1. Add `BrainImageScale(ImageScale)` to `brain_scaling.py`.
2. Implement the metadata constructor (`fieldname`, `scale`, `download`,
   `width`, `height`, `content_type`, `filename`) with `data=None`.
3. Implement the URL helper:
   - pass through `http://`, `https://`, and root-relative `/...` downloads;
   - otherwise join `origin.getURL()` and the relative download;
   - preserve query strings and fragments.
4. Implement `__name__`, `contentType`, `mimetype`, `filename`, `srcset=[]`,
   and no `uid`.
5. Override `tag()` to avoid the inherited eager `self.data._height` /
   `self.data._width` defaults and match `ImageScale.tag` output.
6. Override `title`, `srcset_attribute`, `validate_access`, `index_html`,
   `HEAD`, and `set_headers` per the spec.
7. Add unit tests for URL shapes, tag output, title normalization (plain and
   callable), absent `uid`, `data is None`, and data-serving refusal.

No GitHub writes.

Acceptance: the scale object tests pass and the full suite is green.

## Resolution

Implemented in `src/plone/namedfile/brain_scaling.py`:

- `_scale_url_from_download()`: passes through `http://`, `https://`, and
  root-relative `/...` downloads; joins relative downloads to the metadata
  origin's `getURL()` and preserves query strings/fragments.
- `_extension()`: SVG handling, content-type subtype, download-suffix fallback,
  then `"img"`.
- `BrainImageScale(ImageScale)`:
  - metadata constructor with `fieldname`, `scale`, `download`, `width`,
    `height`, `content_type`, `filename`;
  - `data=None`, no `uid`, `srcset=[]`;
  - `contentType`/`mimetype`, `filename`, readable `__name__`, and `url`;
  - `title`, `srcset_attribute`, `validate_access`;
  - `tag()` matching `ImageScale.tag` without touching file data, including the
    (empty) srcset branch;
  - `index_html`, `HEAD`, and `set_headers` refuse with `NotFound`.
- Documented that `.data` is None and no storage `uid` is exposed.

Tests cover constructor/naming, URL pass-through/join/query/fragment, tag
defaults and overrides, actual `ImageScale.tag` parity, title normalization,
data/uid absence, access no-op, and data-serving refusal.

Verification:

- `test_brain_images`: 39 tests, 0 failures.
- Full suite: 176 tests, 0 failures, 0 errors, 1 pre-existing skip.
- `tox -e lint`: all hooks pass.

Review accepted: the subclass and the small duplicated tag/extension logic are
required by the approved design (do not modify `ImageScale`); the URL rule is
intentionally stricter than `NavigationRootScaling`'s inline check. Review
fixes: documented `.data`/`uid`, added a real `ImageScale` parity test, hoisted
test URL constants, renamed the URL-helper parameter, removed the class-level
`data` and the unused `**info`, and added the srcset branch to `tag()`.

No GitHub writes.
