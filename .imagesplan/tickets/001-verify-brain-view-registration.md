---
id: R1
title: "Verify brain view registration and resolution"
type: research
mode: AFK
status: closed
claimed_by: research-agent-R1
blocked_by: []
---

## Question

Confirm the minimal, non-conflicting registration that makes
`getMultiAdapter((brain, request), name="images")` and the equivalent lookup for
`plone.app.contentlisting` wrappers resolve to a brain-aware `@@images` view.

Investigate:

1. The existing registration `browser:page name="images"
   for="plone.namedfile.interfaces.IImageScaleTraversable"` in
   `src/plone/namedfile/scaling.zcml`. Can a second `images` page registered for
   `Products.ZCatalog.interfaces.ICatalogBrain` coexist? Which one wins for a
   brain, and for a contentlisting wrapper?
2. For `plone.app.contentlisting.catalog.CatalogContentListingObject`
   (`IContentListingObject`), does
   `getMultiAdapter((wrapper, request), name="images")` resolve if registered
   for `IContentListingObject`? Does its `__getattr__` delegate to the brain or
   wake the object? Is `getDataOrigin()` the right way to reach the brain?
3. Does `browser:page` need `allowed_attributes`, a browser layer, or a specific
   permission for programmatic `getMultiAdapter` calls? What does the existing
   page use?
4. Prior art: `NavigationRootScaling` in `src/plone/namedfile/scaling.py`,
   `cs.srcset`'s helper in `/home/erral/dev/images/cs.srcset`, and Plone
   REST API / Volto summary serializers. How do they reach brain image scales?
   What registration or traversal patterns do they use?
5. Any conflict with `for="*"` pages or adapters, and any Zope 5 / Plone 6.2
   gotchas.

Deliverable: a recommended registration set (interfaces + ZCML), the resolution
order for plain brains and contentlisting wrappers, and a short proof strategy
(test snippet) for the view and test-plan tickets. Cite exact files/lines and
upstream URLs.

## Resolution

Register two named `images` pages pointing at one brain-aware view class: one
`for="Products.ZCatalog.interfaces.ICatalogBrain"`, one
`for="plone.app.contentlisting.interfaces.IContentListingObject"` guarded by
`zcml:condition="installed plone.app.contentlisting"`. Both coexist with the
existing `IImageScaleTraversable` page; a plain brain matches only the
`ICatalogBrain` page, and a contentlisting wrapper matches only the
`IContentListingObject` page. Keep `permission="zope2.View"` and expand
`allowed_attributes` to `scale tag srcset picture getImageSize available_sizes
modified`. Programmatic `getMultiAdapter` does not check permission; the
permission and allowed attributes matter for traversal/ZPT. For
`CatalogContentListingObject`, use `getDataOrigin()` and verify
`ICatalogBrain.providedBy(origin)` before reading metadata; it can return an
already-woken real object, and `IContentListingObject` also covers
`RealContentListingObject`. Full evidence and test snippets:
[research/R1-brain-view-registration.md](../research/R1-brain-view-registration.md).
