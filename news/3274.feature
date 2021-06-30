Prevent stored XSS from file upload (svg, html).
Do this by implementing an allowlist of trusted mimetypes.
You can turn this around by using a denylist of just svg, html and javascript.
Do this by setting OS environment variable ``NAMEDFILE_USE_DENYLIST=1``.
From `Products.PloneHotfix20210518 <https://plone.org/security/hotfix/20210518/reflected-xss-in-various-spots>`_.
[maurits]
