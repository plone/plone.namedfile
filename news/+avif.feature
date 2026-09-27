Offer every image as AVIF, generated on demand.
`<scale>.avif` scale names serve an AVIF twin of any scale.
Picture tags get an `image/avif` source in front of each source, and `tag()` wraps the `<img>` in a `<picture>` with an AVIF source.
Uploaded AVIF images get a JPEG fallback (PNG with alpha) for browsers without AVIF support.
Needs Pillow 11.2+ and the `target_format` support of plone.scale.
Set the environment variable `NAMEDFILE_AVIF=0` to turn the markup off.
@MrTango
