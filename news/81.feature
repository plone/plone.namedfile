Add new interface ``plone.namedfile.interfaces.IPluggableFileFieldValidation`` and ``plone.namedfile.interfaces.IPluggableImageFieldValidation``.
Refactored: the fields validation now looks for adapters with this interfaces adapting field and value.
All found adapters are called.
The image content type checker (existed before) is by now the only adapter implemented and registered so far.
Other adapters can be registered in related or custom code.
[jensens]
