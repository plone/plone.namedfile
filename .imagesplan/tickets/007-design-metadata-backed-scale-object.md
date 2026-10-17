---
id: D2
title: "Design the metadata-backed scale object"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R2, R3]
---

## Question

Design the object returned by brain `scale()` and the metadata-backed
`ImageScale`-compatible API.

Decide:

- A dedicated `BrainImageScale` subclass versus making `ImageScale.data`
  optional or passing a data shim.
- Required API: `url`, `width`, `height`, `absolute_url`, `tag()`,
  `srcset_attribute()`, and any attributes consumers rely on.
- How to build the URL from the metadata `download` path and the brain URL,
  including virtual hosting and absolute versus relative URLs.
- How to avoid every access to file data and `data.contentType`.
- Compatibility with code that expects an `ImageScale` instance.
- Security behavior of the scale object itself.

Inputs: "Map image_scales metadata lifecycle and staleness" and "Assess
metadata-only picture() feasibility".

Output: a class contract, URL construction rules, and test expectations.

## Resolution

### Class

Add `BrainImageScale(ImageScale)` to `src/plone/namedfile/brain_scaling.py`.
Do not modify `ImageScale`. The subclass keeps `isinstance(scale, ImageScale)`
working for consumers while never touching file data.

### Constructor

```python
class BrainImageScale(ImageScale):
    data = None

    def __init__(
        self,
        context,
        request,
        *,
        fieldname,
        scale=None,
        download=None,
        width=None,
        height=None,
        content_type=None,
        filename=None,
        **info,
    ):
        ...
```

`context` is the metadata origin (the brain), not the contentlisting wrapper.
The caller (`BrainImageScaling`) resolves the metadata entry and passes its
values. The constructor assumes the entry is usable; deciding whether to fall
back belongs to the fallback-matrix ticket.

Set:

- `self.context`, `self.request`, `self.fieldname`, `self.scale`,
  `self.download`, `self.width`, `self.height`.
- `self.contentType = content_type` and `self.mimetype = content_type`.
- `self.filename = filename`.
- `self.data = None` (documented; no bytes are available on this path).
- `self.srcset = []`.
- `self.extension`: `svg` for `image/svg+xml`, otherwise the subtype from
  `content_type`, falling back to the suffix in `download`, then `"img"`.
- `self.__name__`: `<fieldname>.<ext>` for the original, or
  `<fieldname>-<scale>.<ext>` for a named scale.
- `self.url` via the URL helper below.
- No `uid` attribute. Document that metadata scales have no storage UID.

### URL helper

```python
def _scale_url_from_download(origin, download):
    if download.startswith(("http://", "https://", "/")):
        return download
    return f"{origin.getURL().rstrip('/')}/{download.lstrip('/')}"
```

- Use the metadata origin's `getURL()` so virtual hosting is handled by the
  brain/request.
- Leave absolute (`http://`, `https://`) and root-relative (`/...`) downloads
  unchanged.
- Preserve query strings and fragments; do not split them off.
- The URL always points at the real object, not at the brain.

### Overrides

- `tag(...)`: override the inherited method. `ImageScale.tag` evaluates
  `self.data._height`/`self.data._width` as eager default arguments, which would
  fail with `data=None`. Use `self.height`/`self.width` when the caller does not
  pass explicit values, then build the same attribute list as `ImageScale` and
  call `_image_tag_from_values`. Keep `alt`/`title` defaults and `css_class`
  behavior identical to `ImageScale.tag`.
- `title`: return `context.Title` normalized for both shapes — call it when it
  is callable (contentlisting wrapper), otherwise use the plain value (brain);
  return `""` when absent.
- `srcset_attribute()`: return `""` on the metadata path. HiDPI behavior is
  owned by "Specify the HiDPI include_srcset API".
- `validate_access()`: no-op on the metadata path. The security ticket owns the
  final policy; this must not call `guarded_getattr` on the brain and must not
  wake the object.
- `index_html()`, `HEAD()`, `set_headers()`: raise `NotFound` with the scale
  name/request. A metadata scale never serves bytes; the tag URL points at the
  real object, where normal serving and permission checks apply.
- `_should_force_download()` may stay inherited but is unreachable because
  `set_headers` is overridden. Do not rely on it.
- `absolute_url()` is inherited and returns `self.url`.

### Compatibility notes

- `.data` is `None` and `.uid` is absent on metadata scales; document this.
- `.width`, `.height`, `.url`, `.absolute_url()`, `.tag()`,
  `.srcset_attribute()`, `.title`, `.fieldname`, `.filename`, `.contentType`,
  and `.mimetype` are the supported surface.
- Do not synthesize HiDPI `srcset` here; that decision belongs to the HiDPI
  ticket.
