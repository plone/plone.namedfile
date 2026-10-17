# R2 - `image_scales` metadata lifecycle and staleness

## Scope and pinned evidence

This note describes the contract exposed by
`brain.image_scales` and the scale storage that backs its URLs, as used by
`plone.namedfile` 8.1.2-dev on Plone 6.2.

Local tree:

- `plone.namedfile` HEAD `2010c047e53ce3f74a96e21692e4ea4d7a169ede`
  (2026-08-21, "Back to development: 8.1.2").
- Files cited by path and line are in
  `/home/erral/dev/images/plone.namedfile`.

Upstream refs used below:

- `Products.CMFPlone` master at `3d13c6c67117ca68c0204abd54165520f385654b`
  (2026-10-14).
- `plone.scale` 5.1.0 at `8e6ea5993c85e7f94d159e6a5c72386fa8ab7236`
  (`setup.py` still allows `plone.scale[storage]>=4.2.0`; the lifecycle code
  described here is present in both 4.2.0 and 5.1.0).
- `Products.ZCatalog` at `9538b7772225689bb4cdbfaf46055c77d2d57f1c`,
  `Missing` at `4682baafc3a783ff2cc8166e46d3f1e65d67a0fd`,
  `Record` at `b07f64db23ff08e6620ea5c720ce61853723ac93`.
- `plone.indexer` at `3aebb60b99f3882f38cab4b66d4e58cfed2d5a7b`.
- `plone.app.upgrade` at `f5b7e6c26b705bfd2d5815dcd621b06d2c0eb22d`.
- `plone.app.contentlisting` at
  `b2b0213b7e8f542c955dcb6a306c12c2c4ae8005`.

## 1. Exact metadata contract

### 1.1 Top level

When metadata exists, the brain column is a `PersistentMapping`:

```text
brain.image_scales = {
    "<fieldname>": [ <entry>, ... ],
    ...
}
```

- The mapping is built by the CMFPlone indexer:
  `Products.CMFPlone/image_scales/indexer.py:9-22`, which wraps the adapter
  result in `PersistentMapping`.
- Keys are schema field names, including fields inherited from behaviors;
  the mapping covers every field whose `IImageScalesFieldAdapter` returned a
  non-empty result. See `image_scales/adapters.py:20-33` and the
  `image1`/`image2` test in
  `image_scales/tests/test_image_scales_metadata.py:134-154`.
- A field with no image is omitted, not represented by a key with `None`.
  `ImageFieldScales.__call__` returns `None` for an empty value
  (`src/plone/namedfile/adapters.py:44-47`), and the content adapter skips
  false-y field results (`image_scales/adapters.py:29-32`).
- If the content adapter returns no fields at all, the indexer raises
  `AttributeError`, so the catalog column is left as `Missing.Value`
  (`image_scales/indexer.py:19-21`). This is asserted in
  `test_image_scales_metadata.py:121-132`: a News Item with no image has
  `news_brain.image_scales == Missing.Value`.

When metadata does **not** exist the attribute is `Missing.Value`, not
`None` and not an empty dict. This is a catalog metadata default:
`Products.ZCatalog/Catalog.py:410-419` uses `getattr(object, name, MV)`, and
the CMFPlone indexer intentionally raises `AttributeError` to select it.

### 1.2 One field entry

For each field, the value is a list of dictionaries, one dictionary per
image. The default image field adapter always returns exactly one dictionary:

```python
[
    {
        "filename": "dummy.gif",          # str or None
        "content-type": "image/gif",      # str
        "size": 168,                      # int, bytes
        "download": "@@images/image-16-<md5>.gif",  # str (usually), relative
        "width": 16,                      # int, original pixels
        "height": 16,                     # int, original pixels
        "scales": {
            "listing": {
                "download": "@@images/image-16-<md5>.gif",
                "width": 16,
                "height": 16,
            },
        },
    }
]
```

Evidence:

- Construction: `src/plone/namedfile/adapters.py:58-78`.
- Exact keys and types asserted by local
  `src/plone/namedfile/tests/test_adapters.py:67-97`. The test pops
  `download` and `scales` and compares the rest to the dictionary above.
- Nested scale keys are exactly `download`, `width`, `height`
  (`test_adapters.py:89-97`); there is no per-scale `content-type` or
  `filename`.
- The CMFPlone integration test checks the same outer shape and
  `content-type` (`test_image_scales_metadata.py:55-70, 121-132`).

Type details:

| Key | Type | Meaning |
| --- | --- | --- |
| `filename` | `str \| None` | Original uploaded filename (`image.filename`). |
| `content-type` | `str` | Original MIME type (`image.contentType`). |
| `size` | `int` | Original size in bytes (`image.getSize()`). |
| `download` | `str \| None` | URL/path for the original image. Normally relative `@@images/<uid>.<ext>`; `None` can occur if pre-scaling a corrupt/unreadable image returns no scale. |
| `width` | `int` | Original pixel width. |
| `height` | `int` | Original pixel height. |
| `scales` | `dict[str, dict]` | Named scale -> `{download, width, height}`. |

Important URL detail: the stored `download` is normally a **relative path**,
not an absolute URL. `_scale_view_from_url` strips `context.absolute_url()`
and leading slashes (`adapters.py:131-136`). The changelog records this as
intentional: "Do not use full url in `image_scales` dictionary"
(`CHANGES.rst:409`). Consumers must join it to the object's URL, e.g.
`f"{brain.getURL()}/{download}"`, as `NavigationRootScaling` does at
`src/plone/namedfile/scaling.py:966-970`.

The one exception is a custom `_scale_url` override that returns an absolute
URL (for example Thumbor/CDN, `scaling.py:109-130`); the metadata then contains
that absolute URL because the replace/lstrip is a no-op. Consumers must accept
both relative and `http(s)` values, exactly as `NavigationRootScaling` checks
`data["download"].startswith("http")`.

### 1.3 Which named scales are present

`ImageFieldScales.get_scales` reads `plone.allowed_sizes` from the registry,
parses `"name width:height"` entries, and only includes a scale when its
configured width is not larger than the original width
(`adapters.py:26-33, 80-118`). For each included scale it calls
`@@images.scale(..., pre=True, include_srcset=False)` and records the
**actual** dimensions returned, preserving aspect ratio.

Consequences:

- `scales` may be `{}` for a small image (or a corrupt image) even though the
  original entry exists.
- A configured named scale that is wider than the original is absent. A brain
  view cannot produce that named scale from metadata; the object view would
  return the original or a same-size result, which is why the adapter skips it
  (`adapters.py:86-93`; asserted in
  `test_adapters.py:135-140` and
  `test_image_scales_metadata.py:88-102`).
- No old-style HiDPI `2x`/`3x` entries are stored. `NavigationRootScaling`
  refuses the metadata path when HiDPI is configured and falls through to the
  object (`scaling.py:919-940`).

### 1.4 `Missing.Value` and absent structures

There are four different "no answer" states; a view must distinguish them:

1. `brain.image_scales is Missing.Value` - no metadata for this content at all
   (no image fields, all empty, old schema, or skipped metadata update).
2. `brain.image_scales` is a mapping, but `fieldname not in it` - that field
   has no image or no adapter.
3. `fieldname in image_scales`, but `scales` lacks the requested name - the
   scale was not generated/configured/was larger than the original.
4. The field entry list is empty or malformed - not produced by the stock
   adapter, but should be handled defensively.

Detection:

- `Missing.Value` is falsy (`Missing/__init__.py:26-27`), so the existing
  guard `if not getattr(brain, "image_scales", None): return` in
  `NavigationRootScaling` (`scaling.py:944-948`) catches `Missing.Value`,
  `None`, and an empty mapping.
- `Missing.Value` is not `None`; equality is identity-based
  (`Missing/__init__.py:29-32`). Prefer an explicit check when the distinction
  matters: `scales is Missing.Value or not scales`.
- Do not use `in`, `.get()`, or indexing on `Missing.Value`. It has no mapping
  protocol; `fieldname in Missing.Value` raises `TypeError`. Guard before any
  mapping access.
- Avoid relying on `Missing.Value.__getattr__` either: for alphabetic attribute
  names it returns itself, which can silently look like a value rather than an
  error (`Missing/__init__.py:58-74`).

## 2. When the metadata is written

The metadata is a snapshot written during catalog metadata updates, not on
every request and not in a background job.

Sequence:

1. `image_scales` is a catalog metadata column, not an index:
   `Products.CMFPlone/profiles/default/catalog.xml:227`
   (`<column value="image_scales" />`).
2. The named `image_scales` indexer is registered in
   `Products.CMFPlone/image_scales/configure.zcml:6-10`.
3. `CatalogTool.catalog_object` wraps the content in `IIndexableObject`
   (`Products.CMFPlone/CatalogTool.py:311-329`; wrapper in
   `plone.indexer/wrapper.py:38-57`). While `Catalog.updateMetadata` builds the
   metadata record, `recordify` asks the wrapper for every column name
   (`Products.ZCatalog/Catalog.py:278-305, 410-419`). The wrapper resolves the
   named indexer, so `image_scales` is computed then.
4. The indexer calls the content adapter, which walks every schema field and
   calls its `IImageScalesFieldAdapter` (`image_scales/adapters.py:20-33`).
5. The namedfile field adapter calls `@@images.scale(..., pre=True)` for the
   original and for each allowed scale (`adapters.py:80-129`). Because
   `pre=True`, this goes to `AnnotationStorage.pre_scale`, **not**
   `AnnotationStorage.scale` (`src/plone/namedfile/scaling.py:649-660`).
6. `pre_scale` computes the UID and dimensions from the original image, writes
   an info dict with `data=None`, and stores it in the object's `plone.scale`
   annotations (`plone.scale/storage.py:220-269`). No Pillow work and no image
   bytes are produced. This is the lazy `pre_scale` behavior.

Therefore cataloging an object:

- writes the metadata tuple into the catalog,
- pre-registers UID/dimension info in the object annotation,
- does not render pixels.

The first HTTP request for a metadata URL later calls `get_or_generate`, which
notices `data is None`, reconstructs the scale parameters from the stored
`key`, and calls `generate_scale` (`storage.py:324-339`). That is when Pillow
actually runs.

When is it re-written?

- On `catalog_object` / `reindexObject` when metadata update is enabled
  (`Catalog.catalogObject(..., update_metadata=True)` is the default,
  `Catalog.py:307-340`).
- Standard Plone content edits trigger reindexing. A direct attribute write,
  a write with `update_metadata=False`, or a migration that does not reindex
  will leave the old metadata in place.
- The Plone 6 upgrade explicitly adds the column and refreshes metadata:
  `update_catalog_for_image_scales` in
  `plone.app.upgrade/v60/alphas.py:383-407`; setting
  `UPDATE_CATALOG_FOR_IMAGE_SCALES=0` skips the refresh. That is a documented
  way to end up with an unpopulated column.

There is no metadata refresh triggered by reading a brain, and no invalidation
hook from scale storage back into the catalog.

## 3. UID URLs, storage, and staleness

### 3.1 UID format and URL shape

Storage UIDs are deterministic:

```text
<fieldname>-<dimension>-<md5-hex>
```

- `fieldname` defaults to `"image"` if absent.
- `dimension` is `width`, else `scale`, else `0`
  (`plone.scale/storage.py:200-218`).
- The MD5 input is `tuple(sorted(parameters.items()))` with the current
  `modified` value added; incoming `modified` is discarded first
  (`storage.py:200-214`).

A rendered scale URL is:

```text
<object URL>/@@images/<uid>.<extension>
```

`ImageScale._scale_url` builds it (`src/plone/namedfile/scaling.py:109-130`).
The extension comes from the original/current content type (SVG is special-
cased). Metadata stores the same URL with the object base stripped.

`modified` here means the value returned by the namedfile scaling adapter:

- `ImageScaling.modified(fieldname)` uses `field.modified` if the image value
  has it, otherwise `context._p_mtime`, converted to DateTime milliseconds
  (`src/plone/namedfile/scaling.py:601-617`).
- `ModifiedPropertyMixin.modified` returns `_modified / 1000` if `_modified`
  exists, else `_p_mtime` (`src/plone/namedfile/file.py:73-79`).
- `_modified` is set in `NamedFile`/`NamedBlobFile` constructors and on every
  `_setData` (`file.py:181, 190, 339, 357`).

So the UID covers the field revision plus the scale parameters. The same
field revision and same parameters always produce the same UID; changing the
field data updates `_modified`, which changes the UID. The UID is stable for a
given revision, not stable across edits.

Tests confirm the invalidation behavior:

- Different width/height parameters produce different scales.
- Changing the object `modified` alone does not invalidate a scale.
- Changing the image value's `_modified` invalidates it.
- If `_modified` is absent, `_p_mtime` is the fallback.
  See `tests/test_scaling.py:712-754`.

### 3.2 `pre_scale`, `scale`, and `get_or_generate`

- `pre_scale` returns the existing info if it is not older than the current
  field modification (`_modified_since(info["modified"])` false). Otherwise it
  creates a new info record with `data=None` and a new wall-clock `modified`
  (`storage.py:220-269`). It does not generate pixels.
- `scale` is the synchronous "give me usable data" path: it looks up the
  current UID, falls back to a hash lookup for old-style entries, and returns
  existing data only when it is present and not stale. Otherwise it calls
  `generate_scale` (`storage.py:307-322`).
- `generate_scale` runs the image factory, runs cleanup, and stores data with
  `modified = self.modified_time` (the field modification time, or wall clock
  if unavailable) (`storage.py:271-305`).
- `get_or_generate(uid)` is the URL-serving path. It **does not check
  staleness** on purpose: an old cached page may still request the URL, so
  existing generated data is returned. If no data exists, it regenerates using
  the stored parameters under that same UID. If the UID is not in storage, it
  returns `None` (`storage.py:324-339`; the interface docstring says only
  pre-registered UIDs are accepted, `storage.py:63-70`).

The last point is the key distinction:

- UID stability is not a guarantee that the URL will always resolve. It only
  guarantees that, if parameters and field revision are unchanged and the
  storage entry is (re)created by `pre_scale`, the same UID is produced.
- Metadata cannot reconstruct a scale from a UID alone. There are no UID
  parameters in the catalog metadata. If storage has been cleared, the URL
  404s until something calls `pre_scale`/`scale` again.

### 3.3 Invalidation, cleanup, and clearing

- Invalidation is logical: an old scale is not deleted just because the field
  was modified. A new field revision produces a new UID; old entries remain.
- `_cleanup(fieldname)` runs inside `generate_scale`, not on reads or
  `pre_scale` (`storage.py:280-283, 341-360`). It deletes entries for the same
  fieldname when the current field modification time is more than one day
  after the entry's `modified` (`KEEP_SCALE_MILLIS = 24*60*60*1000`,
  `storage.py:24, 358-360`). It deliberately leaves other fields alone.
- Because cleanup is opportunistic, "kept for one day" is the intent, not a
  guaranteed TTL. If no later scale generation happens for that field, old
  entries may remain much longer. Conversely, once cleanup does run, an old
  cached-page URL can start returning 404.
- `@@images-clear` calls `AnnotationStorage.clear()`
  (`src/plone/namedfile/scaling.py:1000-1012`), removing all stored scale info
  for that object. Metadata is not updated by this action, so catalog URLs
  become dangling immediately.
- Re-cataloging after a clear can call `pre_scale` again. If the field revision
  is unchanged, that recreates the same UID with `data=None`, and the URL
  becomes usable again on the next request. Without a re-catalog, the metadata
  URL cannot regenerate itself.
- Concurrent writes use `ScalesDict._p_resolveConflict`; conflicts can raise
  `ConflictError` (`storage.py:72-135`). This is not part of the normal read
  path but is relevant to writes during cataloging/scaling.

### 3.4 Can a metadata URL 404?

Yes. At least these paths lead to a missing scale:

| Situation | Result |
| --- | --- |
| UID was never pre-registered (hand-made/incomplete metadata) | `get_or_generate` returns `None`; publisher raises `NotFound` (`scaling.py:465-486`). |
| `@@images-clear` was run and no subsequent `pre_scale` recreated the entry | 404. |
| The entry was deleted by `_cleanup` after the one-day cutoff | 404. |
| The image field is now empty and the entry has no generated `data`; regeneration finds no original value | 404. |
| The object was moved/deleted and the catalog was not updated | `brain.getURL()` points at a stale path; the HTTP request 404s before scale storage is consulted. |
| User cannot view the object/field at serve time | Usually `Unauthorized` rather than 404. The `@@images` page requires `zope2.View` (`scaling.zcml:11-18`), and `ImageScale.index_html` calls `validate_access` -> `guarded_getattr` (`scaling.py:230-237, 584-587`). |

The important case for a metadata-first view: **metadata can be valid-looking
and still point at a 404 URL** after a storage clear or cleanup. Metadata
supplies the shape and the historical URL; it cannot prove the storage entry
still exists.

### 3.5 Staleness matrix

| Condition | What the brain returns | What a metadata URL may do |
| --- | --- | --- |
| Normal create/edit with reindex | Current snapshot and current UIDs | 200; may generate lazily. |
| Field edited, catalog reindexed | New UID/dimensions; old metadata replaced | Old cached URL usually still 200 until cleanup; may serve stale bytes if data was already generated. New URL 200. |
| Field edited without reindex | Old snapshot | Old UID may serve previously generated stale bytes; if only pre-registered (`data=None`), it regenerates from the **current** image under the old UID; after cleanup it 404s. |
| Direct blob/data mutation bypassing `_modified` | Metadata may not change even after reindex, because `modified` did not change | Old URL and old scale data can persist as if the image never changed. |
| `allowed_sizes` changed, no reindex | Old scale names/dimensions remain in metadata | Existing old URLs may work; new configured scales are absent until reindex. |
| Object moved/deleted without recatalog | Old path in `getPath()`/`getURL()` | 404 from the object path, regardless of storage. |
| Storage cleared, no recatalog | Old snapshot | 404 until `pre_scale` re-registers the UID. |
| Storage cleaned by `_cleanup` | Old snapshot if no reindex | 404 for the deleted UID. |
| Object reindexed after image removed | `Missing.Value` or field absent | Old URL can still serve until cleanup if data exists, then 404. |

## 4. Multiple entries per field (relation lists)

The list exists because a custom `IImageScalesFieldAdapter` may return more
than one image for a field. The namedfile adapter comment is explicit:

> "Return a list with one dictionary. Why a list? Some people feel a need in
> custom code to support a different adapter for RelationList fields. Such a
> field may point to three images. In that case the adapter could return
> information for all three images, so a list of three dictionaries. The
> default case should use the same structure."
> - `src/plone/namedfile/adapters.py:62-68`

Facts:

- The stock image field adapter always returns a one-element list.
- For a relation-list/custom adapter, list order is adapter-defined. There is
  no `primary`, `is_primary`, or ordering contract in the metadata schema, and
  no way to tell from `image_scales` alone which entry is canonical.
- `NavigationRootScaling` always uses entry `[0]`; on `KeyError`/`IndexError`
  its metadata helper returns `None`, and `tag()` then falls back to
  `brain.getObject()`:
  `src/plone/namedfile/scaling.py:909-916, 949-956`. Its comment says this
  "probably makes the most sense in that corner case as well".
- Therefore an existing precedent is "first entry", but it is a policy, not a
  guarantee from the data. A single-field view should not silently assume
  first-is-primary for arbitrary multi-entry fields unless that policy is
  explicitly specified. This is a decision for the multi-image ticket; R2
  only establishes that metadata does not encode the answer.

## 5. Security and wake-up

### 5.1 Reading metadata

`brain.image_scales` is a catalog `Record` value. `AbstractCatalogBrain`
inherits `Record.__getattr__`/`__getitem__`
(`Products.ZCatalog/CatalogBrains.py:35-100`;
`Record/__init__.py`), and the value is part of the catalog metadata tuple
built by `recordify` (`Catalog.py:410-419`). Reading it:

- does not call `brain.getObject()`,
- does not load the content object's state, annotations, or blobs from ZODB,
- does not run `guarded_getattr` on the image field.

It does, of course, load the catalog's stored metadata record. The "zero
wake-up" guarantee means zero content-object wake-up on the metadata path, not
zero catalog access.

`CatalogContentListingObject` also tries the brain first:
`__getattr__` looks up the attribute on the brain and only falls back to the
real object if the brain has no such attribute
(`plone.app.contentlisting/catalog.py:38-51`). In Plone 6.2 the column exists,
so `listing_item.image_scales` returns the brain value (or `Missing.Value`)
without waking the object. On an older catalog without the column,
`getattr(brain, "image_scales", sentinel)` misses and the wrapper calls
`getObject()`, waking the object (`catalog.py:45-50, 61-70`).

### 5.2 `brain.getObject()`

`AbstractCatalogBrain.getObject()`:

- uses `unrestrictedTraverse` for the parent path,
- uses `restrictedTraverse` for the final object (`CatalogBrains.py:66-91`),
- documents that it returns `None` if the object was deleted/moved without
  recataloging or if the user is not authorized.
- `_unrestrictedGetObject()` exists but is not the default
  (`CatalogBrains.py:52-64`).

So the fallback does perform a real security traversal on the content object
(and wakes it), while the metadata path does not. Do not use the fallback just
to re-check permissions unless that is an explicit requirement; and do not use
unrestricted catalog results for user-facing brain lists, because metadata
access itself performs no per-object permission check. The catalog query
(`allowedRolesAndUsers`) is the security boundary for metadata.

The eventual scale request is checked separately: `@@images` is registered
with `zope2.View`, and `ImageScale.index_html` validates the field with
`guarded_getattr`. Rendering a tag from metadata therefore does not grant
access to image bytes; the browser's follow-up request is still guarded.

## 6. Conditions where metadata can and cannot answer

### Can answer (no `getObject()`)

- Stock `NamedBlobImage`/`NamedImage` field with a non-empty value.
- `image_scales` is a mapping, the fieldname is present, and the entry list has
  exactly one entry.
- Original image request: use the entry-level `download`, `width`, `height`,
  `content-type`, `filename`, `size`.
- Named scale request: the requested name is a key in `entry["scales"]`.
- `pre=True`: metadata already reflects the pre-registered scale; the view can
  return a metadata-backed scale object without generating pixels.
- Default mode (`"scale"`), standard allowed sizes, no HiDPI/srcset.
- Render-time alt/title limited to catalog metadata such as `brain.Title`
  (which `NavigationRootScaling` uses at `scaling.py:958-963`) and static
  overrides supplied by the caller.
- Listing/cached-page URL rendering where a rare dangling URL is acceptable.

### Cannot answer (must return `None`, raise, or fall back)

- `Missing.Value`, `None`, or no `image_scales` attribute.
- Fieldname absent from the mapping (empty image or no adapter).
- Named scale absent from `entry["scales"]` (larger than the original,
  incorrectly configured, corrupt image, or metadata written under a different
  `allowed_sizes`).
- Explicit `width`/`height` that do not correspond to a stored scale.
- Any non-default `mode` (`cover`, `contain`, crop/fill variants): metadata
  was generated with the default scale mode and does not contain arbitrary
  mode results.
- `include_srcset=True`, HiDPI/2x/3x requests, or `picture()` source-set
  variants: metadata has no `srcset`/variant data. `NavigationRootScaling`
  refuses the metadata path when HiDPI is enabled and falls back to the object
  (`scaling.py:930-935`).
- Multiple entries in the field list without a declared primary policy.
- A requirement to prove the scale still exists / is current (storage clear,
  cleanup, un-reindexed edits).
- A requirement to inspect fresh object state, computed/custom fields,
  descriptions, or per-object permission checks.
- Global `available_sizes` for a field with no image: metadata can only
  enumerate the keys present for that particular image; the registry is not
  stored in the brain.

### Stale but still shaped correctly

The view can still build a tag from these, but it is explicitly a best-effort
metadata answer, not a guarantee that the URL is live:

- Metadata from before an edit that was not reindexed.
- Metadata after `@@images-clear`.
- Metadata after `_cleanup` removed old generated entries.
- Metadata after `allowed_sizes` changed without reindex.
- Metadata for an object that moved/was deleted without recataloging.
- Raw field writes that bypass `_modified`/`_p_mtime` and therefore never
  invalidate the stored scales.

The fallback matrix decision should distinguish "metadata has enough data to
render the requested value" from "metadata proves the value is current and
resolvable". R2 only establishes the latter is not guaranteed.

## 7. Practical resolver rules

These are R2 recommendations for the downstream design tickets, not changes to
the contract:

1. Read `raw = getattr(brain, "image_scales", None)`; if
   `raw is Missing.Value or not raw`, return no metadata answer.
2. Resolve and validate the fieldname before touching the mapping. Do not
   index `Missing.Value`.
3. For a single-image query, require `len(entries) == 1` unless a first-entry
   policy is explicitly chosen and documented; otherwise treat as ambiguous.
4. Prefer `entry["scales"][scale_name]` over matching by width/height. Named
   scales are the only unambiguous key; different configured names may share
   dimensions.
5. Treat `download` as relative unless it starts with `http`/`https`; join
   relative paths to the brain URL.
6. Any request that needs a non-default mode, arbitrary dimensions, srcset,
   HiDPI, live existence, or fresh permissions must take the object fallback
   (or return `None`/raise according to the fallback matrix).
7. Do not cache metadata-driven results longer than the catalog's
   `brain.modified`; `NavigationRootScaling`'s RAM cache key already includes
   context URL, UID, `brain.modified`, fieldname, and kwargs
   (`scaling.py:894-907`). That key is only as fresh as the last reindex.
8. If a fallback is taken, remember that `brain.getObject()` may be `None` or
   raise; `getObject()` is not a safe unconditional dereference.

## 8. Source index

Local:

- `src/plone/namedfile/adapters.py` - field-to-metadata shape, relative URLs,
  allowed-size filtering.
- `src/plone/namedfile/scaling.py` - modified callable, `pre=True`, UID URLs,
  `NavigationRootScaling` metadata path and `[0]` policy.
- `src/plone/namedfile/file.py` - `modified` property and `_modified` writes.
- `src/plone/namedfile/scaling.zcml` - `@@images` permission and storage
  adapter registration.
- `src/plone/namedfile/tests/test_adapters.py` - exact per-field contract.
- `src/plone/namedfile/tests/test_scaling.py` - invalidation, fallback to
  `_p_mtime`, UID traversal.
- `CHANGES.rst:409` - relative URL decision.

Upstream (pinned refs above):

- `Products.CMFPlone/src/Products/CMFPlone/image_scales/indexer.py` - indexer
  and `PersistentMapping`; `AttributeError` -> `Missing.Value`.
- `Products.CMFPlone/src/Products/CMFPlone/image_scales/adapters.py` - field
  iteration and empty-field omission.
- `Products.CMFPlone/src/Products/CMFPlone/image_scales/configure.zcml` -
  named indexer registration.
- `Products.CMFPlone/src/Products/CMFPlone/profiles/default/catalog.xml` -
  metadata column.
- `Products.CMFPlone/src/Products/CMFPlone/image_scales/tests/test_image_scales_metadata.py`
  - `Missing.Value`, shape, multiple fields.
- `plone/plone.scale/src/plone/scale/storage.py` - UID hash, `pre_scale`,
  `generate_scale`, `scale`, `get_or_generate`, cleanup.
- `Products.ZCatalog/src/Products/ZCatalog/Catalog.py` - `recordify` and `MV`.
- `Products.ZCatalog/src/Products/ZCatalog/CatalogBrains.py` - metadata
  read vs `getObject()`/restricted traversal.
- `Missing/src/Missing/__init__.py` - falsiness and identity semantics.
- `plone.indexer/src/plone/indexer/wrapper.py` - how the named indexer fills a
  metadata column.
- `plone.app.upgrade/plone/app/upgrade/v60/alphas.py` - column addition and
  metadata refresh during upgrade.
- `plone.app.contentlisting/src/plone/app/contentlisting/catalog.py` - wrapper
  lookup order and wake-up risk on old catalogs.

## 9. Explicitly not covered / open

- Exact behavior of third-party relation-list `IImageScalesFieldAdapter`
  implementations: none are in the pinned core sources. The multi-entry
  contract above is the core adapter's intended extension point, not a
  standardized ordering.
- Whether specific deployment code unregisters/overrides the `modified`
  callable. The default namedfile scaling path supplies a per-field callable;
  `getMultiAdapter((context, None), IImageScaleStorage)` (used by
  `ImagesTest` and the UID-serving traversal) does not. That difference is
  storage-instance-specific.
- A guaranteed TTL for old UIDs. Cleanup is opportunistic, so only the
  deletion condition is guaranteed, not the timing.
- `picture()` feasibility is R3, not R2. The metadata has no srcset/variant
  fields, but variant-to-scale mapping is a separate investigation.
