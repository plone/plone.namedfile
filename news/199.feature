Extract ``_scale_url()`` method on ``ImageScale`` and ``ImageScaling`` for overridable scale URL generation. Accepts an optional ``scale_info`` dict with scale metadata (width, height, mode, fieldname, mimetype, etc.) so custom image backends (e.g. Thumbor) can generate URLs with full context by overriding a single method.
@jensens
