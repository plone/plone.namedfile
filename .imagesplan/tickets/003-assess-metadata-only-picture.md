---
id: R3
title: "Assess metadata-only picture() feasibility"
type: research
mode: AFK
status: closed
claimed_by: research-agent-R3
blocked_by: []
---

## Question

Assess whether `picture()` can be produced exactly from `brain.image_scales`
without `getObject()`, `uuidToObject()`, or `@@images` traversal.

Investigate:

- `src/plone/namedfile/picture.py`: `get_picture_variants`,
  `Img2PictureTag.create_picture_tag`, `get_allowed_scales`, URL resolution,
  `sourceset`, `additionalScales`, `media`, `sizes`, `lazy`, width/height, and
  class/alt/title handling.
- Existing `picture()` tests in `src/plone/namedfile/tests/test_scaling.py` and
  `test_scaling_functional.py`: exact expected HTML and edge cases.
- Which inputs are unavailable from metadata? Can a resolver replace
  `obj.unrestrictedTraverse("@@images").scale(...)` and `uuidToObject`? What
  happens when a variant requests a scale that is not in `image_scales`?
- Fallback cases and parity risks.

Deliverable: a metadata-only algorithm, or a precise list of blockers.
Recommend whether `picture()` can be no-wake-up or needs a documented fallback.
Include sample expected/actual snippets.

## Resolution

Conditional yes. Exact, no-wake-up `picture()` parity is feasible when every
scale the variant traverses (source targets plus allowed `additionalScales`) is
present in `brain.image_scales[fieldname][0]["scales"]`. URLs then come from
`brain.getURL() + "/" + download` (or an absolute `download`), and target
width/height from the same metadata; `uuidToObject()` and `@@images` traversal
are unnecessary.

The blocker is that catalog metadata intentionally omits configured scales
wider than the original image, while object-backed `picture()` still
pre-registers them with requested-width UID URLs. Consequently default `large`
needs originals >=1600 px, `medium` >=1200 px, and `small` >=1000 px for exact
parity; smaller images (including the existing 200x200 picture fixture) cannot
match. Stale indexes, cleared scale storage, corrupt images, multi-image
`fieldname=None`, and computed titles are additional fallback/risk cases.

Recommendation: metadata-first with a preflight gate on the required scale set;
on failure use the explicit object fallback for exact parity. A zero-wake-up
degraded mode is possible but must be documented as non-parity (skip missing
srcset entries or use legacy `@@images/<field>/<scale>` URLs). Reuse one
`Img2PictureTag` builder with an injected resolver.

Full findings, algorithm, case table, and exact snippets:
[R3-metadata-only-picture.md](../research/R3-metadata-only-picture.md)
