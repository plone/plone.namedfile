Fix auto-sizing for picture variants

Using sizes="auto" on a <source> requires the following <img> to
also have sizes="auto" and loading="lazy".

Automatically set sizes="auto" on <img> when lazy loading is enabled
and the picture variant uses auto-sizing.
