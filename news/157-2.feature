Improve contenttype detection logic for unregistered but common types.

Change get_contenttype to support common types which are or were not registered
with IANA, like image/webp or audio/midi.

Note: image/webp is already a IANA registered type and also added by
Products.MimetypesRegistry.
[thet]
