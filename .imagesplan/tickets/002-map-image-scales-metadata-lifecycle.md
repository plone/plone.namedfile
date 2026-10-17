---
id: R2
title: "Map image_scales metadata lifecycle and staleness"
type: research
mode: AFK
status: closed
claimed_by: research-agent-R2
blocked_by: []
---

## Question

Map the lifecycle, shape, and staleness of `brain.image_scales` well enough to
define the fallback matrix for a metadata-first view.

Investigate:

- `Products.CMFPlone/image_scales/indexer.py` and `adapters.py`, plus
  `plone.namedfile/adapters.py`: exact keys and types, `Missing.Value`, when the
  metadata is written, and whether scale generation is lazy (`pre_scale`).
- `plone.scale.storage.AnnotationStorage.pre_scale`, `scale`, and
  `get_or_generate`; UID URL generation; `modified` callables; what invalidates
  or removes stored scales.
- What happens when metadata exists but the scale was cleared or rebuilt, or the
  object changed without a reindex. Are UID scale URLs stable? Can a metadata
  URL 404?
- Multiple entries per field (relation lists): what does the list mean? Which
  entry should a single-field view use? How does `NavigationRootScaling` handle
  it?
- Security and wake-up: does reading `brain.image_scales` touch only catalog
  metadata? Does `brain.getObject()` use restricted traversal? How should
  `Missing.Value` be detected?

Deliverable: a field-by-field metadata contract and a list of conditions where
metadata can answer, where it cannot, and where it may be stale, with evidence
from code and tests.

## Resolution

`brain.image_scales` is a catalog metadata snapshot (`PersistentMapping` keyed
by fieldname -> list of image dicts; `Missing.Value` when absent), written only
during catalog metadata updates. Each image has `filename`, `content-type`,
`size`, relative `download`, original `width`/`height`, and `scales` (name ->
relative `download`/`width`/`height`). Cataloging calls `pre_scale`, which
pre-registers deterministic UID URLs without generating pixels; the first URL
request generates lazily. UIDs change with the image field's `_modified`, old
scales are kept opportunistically for about a day, and `get_or_generate` serves
stale data by design. Metadata can answer single-entry default-mode named
scales and originals, but not arbitrary dimensions/modes, srcset/HiDPI,
multi-entry ambiguity, cleared/cleaned storage, or freshness/permission
guarantees. Reading the brain does not wake the content object;
`brain.getObject()` uses restricted traversal for the final object.

Full findings, evidence, and fallback conditions:
[R2-image-scales-lifecycle.md](../research/R2-image-scales-lifecycle.md)
