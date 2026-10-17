---
id: D4
title: "Specify field resolution and multi-image metadata"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R2]
---

## Question

Specify how the brain-aware view resolves `fieldname`.

Decide:

- What happens when `fieldname` is omitted, given that a brain has no
  `IPrimaryFieldInfo`. Is there a primary image field, a single-field
  heuristic, or an error?
- When `image_scales` contains multiple image fields, which one is used?
- When one field maps to a list with multiple entries (relation lists), is the
  first entry used, are all entries exposed, or is the case rejected?
- How `Missing.Value`, an empty mapping, and contentlisting wrappers behave.
- What the `available_sizes` property means when fieldname is irrelevant.

Inputs: "Map image_scales metadata lifecycle and staleness".

Output: field-resolution rules with examples and expected return values.

## Resolution

### One resolver

All brain methods use a single field/metadata resolver:

```python
def _resolve_metadata(self, fieldname=None):
    metadata = self._metadata()  # D3: Missing.Value/no-column handled first
    if not metadata:
        return None, None
    if fieldname is not None:
        entries = metadata.get(fieldname)
        if not entries:
            return None, None
        return fieldname, entries[0]
    names = list(metadata.keys())
    if len(names) != 1:
        if len(names) > 1:
            logger.debug(
                "@@images cannot choose a field on this brain: %s", names
            )
        return None, None
    return names[0], metadata[names[0]][0]
```

- `fieldname` given: use it only if it is present and its entry list is
  non-empty. Otherwise return `(None, None)`; do not fall back to another
  field and do not wake the object.
- `fieldname` omitted: use the only field when exactly one exists. Zero fields
  or multiple fields return `(None, None)`. Do **not** prefer a field named
  `image`, and do **not** use `IPrimaryFieldInfo` or `getObject()` to discover a
  primary field.
- `Missing.Value`, an empty mapping, and an absent catalog column are handled by
  the fallback matrix before this resolver.

### Multiple entries per field

- Use `entries[0]` only. This matches `NavigationRootScaling` and is the defined
  behavior for relation-list/custom adapters.
- If `len(entries) > 1`, log at debug level with the fieldname and count. Only
  the first image is supported; a multi-image API is a separate feature.

### Method application

- `scale`, `tag`, `srcset`, `picture`, and `getImageSize` all call this resolver
  after unwrapping the metadata origin.
- If the resolver returns `(None, None)`:
  - `scale`/`tag`/`srcset`/`picture` return `None`;
  - `getImageSize` returns `(0, 0)`.
- `modified(fieldname=None)` accepts the argument for API compatibility but
  ignores it on the metadata path and uses `brain.modified` (falling back to
  `0`).
- `available_sizes` ignores `fieldname`, exactly like the object-backed view.
- No method resolves a field by falling back to the object; that would defeat
  the zero-wake guarantee.

### Documentation

Document that:

- omitting `fieldname` works only when the brain has exactly one image field;
- an explicit `fieldname` is required for multi-image content types;
- relation-list fields expose only their first image;
- fields are not resolved through the object’s primary-field information.

