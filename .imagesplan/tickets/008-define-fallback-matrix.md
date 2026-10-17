---
id: D3
title: "Define the metadata-first fallback matrix"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R1, R2]
---

## Question

Define exactly when the brain-aware view answers from metadata, when it falls
back to `getObject()`, when it returns `None`, and when it raises.

Cover at least:

- `scale` name present, absent, or larger than the original.
- Explicit `width`/`height` that do or do not match a configured scale.
- `mode="scale"` versus `mode="crop"` and any other modes.
- `pre=True`, `include_srcset`, and HiDPI requests.
- Missing field, `Missing.Value`, empty `image_scales`, and no image field.
- Malformed, partial, or stale metadata; scale storage cleared; deleted object.
- Multiple list entries for one field.
- `getObject()` returning `None`, raising `Unauthorized`, or raising another
  exception.
- Logging and the zero-wake-up guarantee for the metadata path.

Inputs: "Verify brain view registration and resolution" and "Map image_scales
metadata lifecycle and staleness".

Output: a decision table that the specification and tests can copy directly.

## Resolution

### Schema-aware "no metadata"

The view distinguishes "this content has no image" from "this catalog cannot
answer":

- If the catalog schema contains `image_scales`: `Missing.Value`, a missing
  field, or an empty entry list means **no image**. Return `None` for
  `scale`/`tag`/`srcset`/`picture`, `(0, 0)` for `getImageSize`, and `0` for
  `modified`. Do **not** wake the object.
- If the catalog schema lacks `image_scales`: metadata cannot answer anything,
  so every request falls back to the object view.
- The schema check must not call `getObject()`. Cache it per view instance or
  request if useful.

`fieldname` resolution (including omitted fieldname and multiple entries) is
owned by "Specify field resolution and multi-image metadata".

### Request matrix

| Request | Behavior |
|---|---|
| `scale` name present in the field's metadata `scales` | metadata |
| `scale` name in `available_sizes` but absent from metadata | fallback to the object (parity for scales wider than the original) |
| `scale` name not in `available_sizes` | return `None` (same as the object view) |
| `scale=None` with no dimensions | original metadata entry |
| explicit `width`/`height` matching a metadata scale or the original | metadata |
| explicit `width`/`height` matching nothing | fallback to the object |
| `scale` plus explicit dimensions | ignore dimensions and take the scale, mirroring the object view's warning behavior |
| `mode` other than `"scale"` | fallback to the object |
| `pre=True` with metadata-answerable dimensions | metadata (no storage access) |
| `include_srcset=True` or HiDPI configured/requested | fallback to the object; the HiDPI ticket owns the exact API |

The metadata path must perform **zero** `getObject()` calls for every row marked
"metadata". `available_sizes`, `getHighPixelDensityScales`, and other inherited
helpers do not by themselves trigger a wake.

**Exception:** `srcset()` has a specific bulk-iteration rule: it skips a
configured scale that is missing from metadata and emits the rest, rather than
falling back the whole call. The selected `scale_in_src` still falls back when
missing. See "Specify srcset parity from metadata".

### Failure, corruption, and staleness

- Malformed metadata (missing `download`, `width`, or `height`, or wrong types):
  fall back to the object.
- `getObject()` returns `None`: return `None` from `scale`/`tag`/`srcset`/
  `picture`, `(0, 0)` from `getImageSize`, and `0` from `modified`.
- `getObject()` raises `Unauthorized`: propagate it. The security ticket owns
  any refinement; do not silently swallow it here.
- Stale metadata whose scale URL later 404s: accept and document. Detecting it
  would require waking or an HTTP check, which defeats the fast path. Storage
  cleanup is the documented cause.
- Log every fallback at debug level with the fieldname, requested scale/
  dimensions, and reason. Do not emit warnings for normal fallbacks.

### Accessors

- `modified(fieldname=None)`: return `DateTime(brain.modified).millis()` when
  the brain has a usable `modified`; otherwise return `0`. Do not fall back just
  to read the object's `_p_mtime`.
- `getImageSize(fieldname=None)`:
  - field present in metadata with `width`/`height`: return those values;
  - field present but dimensions missing/corrupt: fall back to the object;
  - field absent (schema-aware no-image case): return `(0, 0)`.
- `available_sizes`: inherited registry lookup; no fallback.

### Observability

Use a module logger (`logging.getLogger(__name__)`) and debug-level messages
such as `"@@images falling back to object for %s/%s: %s"`. No warnings, no
tracebacks for expected fallback reasons; unexpected exceptions follow the
failure policy above.

