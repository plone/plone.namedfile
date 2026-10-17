---
id: D7
title: "Specify the HiDPI include_srcset API"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R2, R3]
---

## Question

Specify the HiDPI behavior for the brain-aware view.

Settled direction: the metadata path omits old-style 2x/3x `srcset` by default;
an explicit request may fall back to the object.

Decide:

- Where the opt-in lives: a new `include_srcset` keyword on the brain view's
  `tag()`, on `scale()`, or both.
- The default for `tag()`, `srcset()`, `picture()`, and direct `scale(pre=True)`
  calls.
- Whether `include_srcset=True` always falls back to `getObject()`, and what
  happens if the fallback is unavailable.
- The exact signature, behavior table, documentation wording, and tests,
  including a site with HiDPI configured.

Inputs: "Map image_scales metadata lifecycle and staleness" and "Assess
metadata-only picture() feasibility".

Output: the API signature and a behavior table.

## Resolution

### Signatures

Add a named `include_srcset` keyword to both brain methods:

```python
def scale(
    self,
    fieldname=None,
    scale=None,
    height=None,
    width=None,
    mode="scale",
    pre=False,
    include_srcset=None,
    **parameters,
):
    ...

def tag(
    self,
    fieldname=None,
    scale=None,
    height=None,
    width=None,
    mode="scale",
    include_srcset=None,
    **kwargs,
):
    ...
```

`tag()` consumes the keyword and passes it to `scale()`; it is never rendered
as an HTML attribute.

### Behavior table

| Call | HiDPI configured | Behavior |
|---|---|---|
| `include_srcset=None` (default), any `pre` | either | metadata; no HiDPI `srcset`; no wake |
| `include_srcset=False` | either | metadata; no HiDPI `srcset`; no wake |
| `include_srcset=True` | no | metadata; no HiDPI `srcset`; no wake |
| `include_srcset=True` | yes | fall back to the object-backed `scale()`/`tag()`; wake by design |

`None` deliberately ignores the object rule “`pre=True` implies
`include_srcset=True`”. The metadata path never includes HiDPI implicitly.

Use `getHighPixelDensityScales()` (a registry read) to decide whether HiDPI is
configured. An empty list means `include_srcset=True` is a no-op and stays on
the metadata path.

### Implementation

- `include_srcset=False` or `None`: metadata scale/tag; the brain scale's
  `srcset_attribute()` returns `""`.
- `include_srcset=True` and HiDPI configured:
  - `scale()`: delegate the whole call to the object-backed view with the same
    arguments plus `include_srcset=True`, returning its object-backed scale;
  - `tag()`: call the object-backed `scale(..., pre=True,
    include_srcset=True)` and then `.tag(**kwargs)`, so the returned tag
    contains the object's HiDPI `srcset`.
- `include_srcset=True` and no HiDPI: metadata scale/tag, no `srcset`
  attribute.
- Fallback failures follow the fallback matrix: `getObject() is None` ->
  `None`; `Unauthorized` propagates.
- Do not synthesize 2x/3x URLs from metadata; the 2x/3x scales are not in the
  catalog snapshot.

### `srcset()` and `picture()`

- No `include_srcset` keyword.
- Their metadata output remains HiDPI-free.
- Document that HiDPI is a `scale()`/`tag()` concern: `x` descriptors do not
  belong in a width-based `srcset` or a `<picture>` sourceset.

### Documentation and tests

Document the default divergence from the object view and the cost of the
explicit opt-in. Tests must cover:

- HiDPI configured: default and `False` produce no `srcset` and zero wake-ups;
- HiDPI configured: `True` matches the object tag and wakes;
- HiDPI not configured: `True` stays metadata-only and wakes nothing;
- `srcset()` and `picture()` are unaffected;
- `include_srcset` is not emitted as an HTML attribute.
