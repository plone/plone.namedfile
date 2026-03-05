Extract ``_scale_url()`` method on ``ImageScale`` and ``ImageScaling`` for overridable scale URL generation. This allows custom image backends (e.g. Thumbor) to generate direct URLs by overriding a single method.
@jensens
