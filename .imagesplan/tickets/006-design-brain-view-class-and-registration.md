---
id: D1
title: "Design the brain-aware view class and registration"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R1, R4]
---

## Question

Design the class, module, and registration for the brain-aware `@@images` view.

Decide:

- Subclass `ImageScaling` or delegate to it; class and module names.
- Which methods are overridden and which are inherited.
- How the view detects and unwraps a plain brain versus an
  `IContentListingObject` (for example via `getDataOrigin()`).
- The exact ZCML registrations for `ICatalogBrain` and `IContentListingObject`,
  including `allowed_attributes`, permission, and any browser layer.
- How to preserve the existing `IImageScaleTraversable` behavior byte-for-byte.
- Explicitly exclude publisher traversal and serving from the brain path.

Inputs: "Verify brain view registration and resolution" and "Map test
infrastructure and zero-wake-up instrumentation".

Output: a resolution with the exact file/class/registration plan and a list of
object-path behaviors that must remain unchanged.

## Resolution

### Module and class

Create `src/plone/namedfile/brain_scaling.py`:

```python
from Products.ZCatalog.interfaces import ICatalogBrain
from zope.component import getMultiAdapter

class BrainImageScaling(ImageScaling):
    ...
```

`BrainImageScaling` subclasses `ImageScaling` and overrides the metadata-aware
methods added by the later decision tickets. The existing `ImageScaling` class
and `scaling.py` stay untouched. The module imports only `Products.ZCatalog`,
`zope.component`, and what it needs from `plone.namedfile`; it must stay
import-safe when `plone.app.contentlisting` is not installed. Do not import
`plone.app.contentlisting` in this module: detect the wrapper by the
`getDataOrigin` method, which is defined on the wrapper class and does not wake.

### Metadata origin

One helper owns context resolution:

```python
def _metadata_origin(self):
    origin = (
        self.context.getDataOrigin()
        if hasattr(self.context, "getDataOrigin")
        else self.context
    )
    return origin if ICatalogBrain.providedBy(origin) else None
```

Rules:

- Plain brain: no `getDataOrigin`; the context is the brain.
- `CatalogContentListingObject`: `getDataOrigin()` returns the brain, unless it
  has already been woken, in which case it returns the real object. Check
  `ICatalogBrain.providedBy()` and never assume a wrapper origin is a brain.
- `RealContentListingObject`: `getDataOrigin()` returns the real object, so the
  helper returns `None` and the view delegates to the object path.
- The metadata path must never call `getObject()`.

### Object fallback

One helper owns delegation:

```python
def _object_view(self, origin):
    obj = origin.getObject() if ICatalogBrain.providedBy(origin) else origin
    return getMultiAdapter((obj, self.request), name="images")
```

- Callers pass the metadata origin (the brain) or the real object, never the
  wrapper itself.
- Only a brain origin needs the waking `getObject()` call. A real-object origin
  (for example from `RealContentListingObject.getDataOrigin()`) is already the
  object.
- Calling `getMultiAdapter` on the real content object resolves to the existing
  `ImageScaling`, not back to `BrainImageScaling`.
- What to do when `getObject()` returns `None` or raises is left to
  "Define the metadata-first fallback matrix".

### Registration

Add `src/plone/namedfile/brain_scaling.zcml` and include it from
`configure.zcml`. Do not edit `scaling.zcml`.

```xml
<browser:page
    name="images"
    for="Products.ZCatalog.interfaces.ICatalogBrain"
    class=".brain_scaling.BrainImageScaling"
    allowed_attributes="scale tag srcset picture getImageSize available_sizes modified"
    permission="zope2.View"
    />

<configure zcml:condition="installed plone.app.contentlisting">
  <browser:page
      name="images"
      for="plone.app.contentlisting.interfaces.IContentListingObject"
      class=".brain_scaling.BrainImageScaling"
      allowed_attributes="scale tag srcset picture getImageSize available_sizes modified"
      permission="zope2.View"
      />
</configure>
```

- The `ICatalogBrain` registration is unconditional (`Products.ZCatalog` is
  transitive via `Products.CMFCore`).
- The `IContentListingObject` registration is conditional because
  `plone.app.contentlisting` is not a dependency.
- Keep the existing `images` page for `IImageScaleTraversable` and all
  object-backed behavior unchanged. `zope2.View` is correct for anonymous
  listing rendering; `getMultiAdapter` itself does not check the permission.
- No browser layer is needed; the default `IDefaultBrowserLayer` matches Plone
  requests and test requests.

### Traversal

The brain view must not pretend to serve bytes. Override the inherited
publisher/traversal hooks to refuse:

- `publishTraverse(request, name)` raises `NotFound`.
- `traverse(name, furtherPath)` raises `TraversalError`.
- `browserDefault(request)` raises `BadRequest` with a message explaining that
  `@@images` URL serving is only available on real content objects.

Scale URLs stay valid because they point at the real object, not the brain.

### Boundary

This ticket decides structure, registration, origin resolution, and fallback
delegation only. `scale`, `getImageSize`, `modified`, `srcset`, `picture`, and
HiDPI behavior are settled by the later decision tickets.
