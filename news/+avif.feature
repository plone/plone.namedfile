Add AVIF image scales, with a mode in the imaging control panel (registry record `plone.avif_mode`, from plone.base).
`avif_with_fallback`, the default: picture tags get an `image/avif` source in front of each source, generated on demand, and `<scale>.avif` scale names serve the AVIF version of a scale; plain scales and `tag()` are unchanged, and an uploaded AVIF image gets JPEG scales (PNG with alpha) as the fallback.
Each scale in the `image_scales` catalog metadata carries the stable URL of its AVIF version as `avif.download`.
`avif_only`: every scale is encoded as AVIF. `disabled`: no conversion, scales keep the format of the uploaded image, AVIF included.
AVIF scales use the control panel's `avif_quality` and `avif_speed`.
Needs Pillow 11.2+ and the `target_format` and `speed` parameters of plone.scale.
@MrTango
