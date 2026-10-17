---
id: D8
title: "Specify security and unauthorized behavior"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R1, R2]
---

## Question

Specify security semantics for the brain-aware view.

Settled direction: the metadata path performs no extra permission check, the
fallback uses restricted `getObject()`/traversal, and image URLs still enforce
`View` on the real object.

Decide:

- The exact policy and its documentation, including the fact that metadata
  exposure is equivalent to today's catalog/REST `image_scales` exposure.
- Behavior when the user cannot view the object, when the object is deleted, and
  when the field is protected.
- Whether any logging or warning is emitted on permission failures.
- Tests for metadata, fallback, unauthorized URL access, and restricted fields.

Inputs: "Verify brain view registration and resolution" and "Map image_scales
metadata lifecycle and staleness".

Output: the security policy and the test cases.

## Resolution

### Metadata path

- Perform **no extra permission check** before reading `brain.image_scales`,
  `Title`, dimensions, or `download` URLs.
- Document that this is the same exposure as today’s catalog/REST
  `image_scales` output: search results and summaries already carry the
  metadata. The brain view adds no new class of disclosure.
- The generated scale URL still resolves to the real object, where normal
  `View` checks and traversal apply. Rendering a tag does not grant access to
  the bytes.
- Do not add a `guarded` mode. If a project needs stricter behavior, it must use
  the object-backed view or a custom view.

### Field-level permissions

The metadata path does **not** evaluate `guarded_getattr` or the field’s read
permission. Document explicitly:

- the object-backed `@@images` enforces field access through
  `guarded_getattr`;
- the brain-backed view does not, because metadata carries no field-security
  information;
- image fields with non-default read permissions must be rendered through the
  object-backed view;
- this is a documented limitation, not an accidental omission.

Do not attempt to introspect the FTI schema or call `getObject()` to enforce
field permissions on the metadata path.

### Unauthorized and missing objects

- `getObject()` returning `None` (deleted, moved, uncataloged): return `None`
  from `scale`/`tag`/`srcset`/`picture`, `(0, 0)` from `getImageSize`, and `0`
  from `modified`. Do not log a warning.
- `getObject()` raising `Unauthorized`: propagate it from every method,
  including `getImageSize`. Do not convert it to an empty result; an
  authorization failure must not look like “no image”. This matches the object
  view’s behavior and the fallback matrix.
- `RealContentListingObject` and any already-woken wrapper origin take the
  object path and therefore keep their normal permission enforcement.

### Logging

- Do not log permission failures at info/warning level, and never include user
  identities, roles, or object paths beyond what the debug fallback message
  already contains.
- Debug-level fallback reasons may name the fieldname and reason, as decided by
  the fallback matrix.

### Documentation

Add an explicit security section covering:

- metadata is catalog data, already exposed by search/REST summaries;
- image bytes are protected by the real object’s URL;
- field-level read permissions are not enforced on the metadata path;
- `Unauthorized` propagates from fallbacks;
- missing objects yield empty results.

### Tests

- Functional: anonymous/unauthorized users cannot fetch the image bytes from
  the generated scale URL, even though the brain tag rendered metadata.
- Fallback: an `Unauthorized` object raises from `scale`/`tag`/`srcset`/
  `picture`/`getImageSize`.
- Missing object: `getObject() is None` yields the empty-result contract above.
- Field permission divergence: metadata path renders while the object path
  raises, documenting the limitation.
- No wake-ups are introduced on the metadata path by security handling.
