---
id: I3
title: "Implement BrainImageScale and the metadata URL helper"
type: task
mode: AFK
status: open
claimed_by: null
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
