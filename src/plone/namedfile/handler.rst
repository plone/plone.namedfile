plone.supermodel handler
========================

If plone.supermodel is installed, this package will register a handler
for the RichText field.

First, we wire up the handlers::

    >>> configuration = """\
    ... <configure
    ...      xmlns="http://namespaces.zope.org/zope"
    ...      i18n_domain="plone.namedfile">
    ...
    ...     <include package="zope.component" file="meta.zcml" />
    ...     <include package="zope.security" file="meta.zcml" />
    ...
    ...     <include package="plone.namedfile" file="handler.zcml" />
    ...
    ... </configure>
    ... """

    >>> from io import StringIO
    >>> from zope.configuration import xmlconfig
    >>> xmlconfig.xmlconfig(StringIO(configuration))

Then, let's test the fields. Note that 'default' and 'missing_value' are
unsupported::

    >>> from zope.component import getUtility
    >>> from plone.namedfile.field import NamedFile, NamedImage, NamedBlobFile, NamedBlobImage

    >>> from plone.supermodel.interfaces import IFieldExportImportHandler
    >>> from plone.supermodel.interfaces import IFieldNameExtractor
    >>> from plone.supermodel.utils import prettyXML

    >>> from lxml import etree


Named file
----------

::

    >>> field = NamedFile(
    ...     __name__="dummy",
    ...     accept=("audio/ogg", "audio/flac"),
    ...     title=u"Test",
    ...     description=u"Test desc",
    ...     required=False,
    ...     readonly=True
    ... )
    >>> fieldType = IFieldNameExtractor(field)()
    >>> handler = getUtility(IFieldExportImportHandler, name=fieldType)
    >>> element = handler.write(field, u'dummy', fieldType) #doctest: +ELLIPSIS
    >>> print(prettyXML(element))
    <field name="dummy" type="plone.namedfile.field.NamedFile">
      <accept>
        <element>audio/ogg</element>
        <element>audio/flac</element>
      </accept>
      <description>Test desc</description>
      <readonly>True</readonly>
      <required>False</required>
      <title>Test</title>
    </field>

    >>> element = etree.XML("""\
    ... <field name="dummy" type="plone.namedfile.field.NamedFile">
    ...   <accept>
    ...     <element>audio/ogg</element>
    ...     <element>audio/flac</element>
    ...   </accept>
    ...   <description>Test desc</description>
    ...   <missing_value />
    ...   <readonly>True</readonly>
    ...   <required>False</required>
    ...   <title>Test</title>
    ... </field>
    ... """)

    >>> reciprocal = handler.read(element)
    >>> reciprocal.__class__
    <class 'plone.namedfile.field.NamedFile'>
    >>> reciprocal.__name__
    'dummy'
    >>> reciprocal.accept
    ('audio/ogg', 'audio/flac')
    >>> print(reciprocal.title)
    Test
    >>> print(reciprocal.description)
    Test desc
    >>> reciprocal.required
    False
    >>> reciprocal.readonly
    True


Named image
-----------

::

    >>> field = NamedImage(
    ...     __name__="dummy",
    ...     accept=("image/png", "image/webp"),
    ...     title=u"Test",
    ...     description=u"Test desc",
    ...     required=False,
    ...     readonly=True
    ... )
    >>> fieldType = IFieldNameExtractor(field)()
    >>> handler = getUtility(IFieldExportImportHandler, name=fieldType)
    >>> element = handler.write(field, u'dummy', fieldType) #doctest: +ELLIPSIS
    >>> print(prettyXML(element))
    <field name="dummy" type="plone.namedfile.field.NamedImage">
      <accept>
        <element>image/png</element>
        <element>image/webp</element>
      </accept>
      <description>Test desc</description>
      <readonly>True</readonly>
      <required>False</required>
      <title>Test</title>
    </field>

    >>> element = etree.XML("""\
    ... <field name="dummy" type="plone.namedfile.field.NamedImage">
    ...   <accept>
    ...     <element>image/png</element>
    ...     <element>image/webp</element>
    ...   </accept>
    ...   <description>Test desc</description>
    ...   <missing_value />
    ...   <readonly>True</readonly>
    ...   <required>False</required>
    ...   <title>Test</title>
    ... </field>
    ... """)

    >>> reciprocal = handler.read(element)
    >>> reciprocal.__class__
    <class 'plone.namedfile.field.NamedImage'>
    >>> reciprocal.__name__
    'dummy'
    >>> reciprocal.accept
    ('image/png', 'image/webp')
    >>> print(reciprocal.title)
    Test
    >>> print(reciprocal.description)
    Test desc
    >>> reciprocal.required
    False
    >>> reciprocal.readonly
    True


Named blob file
---------------

::

    >>> field = NamedBlobFile(
    ...     __name__="dummy",
    ...     accept=("audio/ogg", "audio/flac"),
    ...     title=u"Test",
    ...     description=u"Test desc",
    ...     required=False,
    ...     readonly=True
    ... )
    >>> fieldType = IFieldNameExtractor(field)()
    >>> handler = getUtility(IFieldExportImportHandler, name=fieldType)
    >>> element = handler.write(field, u'dummy', fieldType) #doctest: +ELLIPSIS
    >>> print(prettyXML(element))
    <field name="dummy" type="plone.namedfile.field.NamedBlobFile">
      <accept>
        <element>audio/ogg</element>
        <element>audio/flac</element>
      </accept>
      <description>Test desc</description>
      <readonly>True</readonly>
      <required>False</required>
      <title>Test</title>
    </field>

    >>> element = etree.XML("""\
    ... <field name="dummy" type="plone.namedfile.field.NamedBlobFile">
    ...   <accept>
    ...     <element>audio/ogg</element>
    ...     <element>audio/flac</element>
    ...   </accept>
    ...   <description>Test desc</description>
    ...   <missing_value />
    ...   <readonly>True</readonly>
    ...   <required>False</required>
    ...   <title>Test</title>
    ... </field>
    ... """)

    >>> reciprocal = handler.read(element)
    >>> reciprocal.__class__
    <class 'plone.namedfile.field.NamedBlobFile'>
    >>> reciprocal.__name__
    'dummy'
    >>> reciprocal.accept
    ('audio/ogg', 'audio/flac')
    >>> print(reciprocal.title)
    Test
    >>> print(reciprocal.description)
    Test desc
    >>> reciprocal.required
    False
    >>> reciprocal.readonly
    True


Named blob image
----------------

::

    >>> field = NamedBlobImage(
    ...     __name__="dummy",
    ...     accept=("image/png", "image/webp"),
    ...     title=u"Test",
    ...     description=u"Test desc",
    ...     required=False,
    ...     readonly=True
    ... )
    >>> fieldType = IFieldNameExtractor(field)()
    >>> handler = getUtility(IFieldExportImportHandler, name=fieldType)
    >>> element = handler.write(field, u'dummy', fieldType) #doctest: +ELLIPSIS
    >>> print(prettyXML(element))
    <field name="dummy" type="plone.namedfile.field.NamedBlobImage">
      <accept>
        <element>image/png</element>
        <element>image/webp</element>
      </accept>
      <description>Test desc</description>
      <readonly>True</readonly>
      <required>False</required>
      <title>Test</title>
    </field>

    >>> element = etree.XML("""\
    ... <field name="dummy" type="plone.namedfile.field.NamedBlobImage">
    ...   <accept>
    ...     <element>image/png</element>
    ...     <element>image/webp</element>
    ...   </accept>
    ...   <description>Test desc</description>
    ...   <missing_value />
    ...   <readonly>True</readonly>
    ...   <required>False</required>
    ...   <title>Test</title>
    ... </field>
    ... """)

    >>> reciprocal = handler.read(element)
    >>> reciprocal.__class__
    <class 'plone.namedfile.field.NamedBlobImage'>
    >>> reciprocal.__name__
    'dummy'
    >>> reciprocal.accept
    ('image/png', 'image/webp')
    >>> print(reciprocal.title)
    Test
    >>> print(reciprocal.description)
    Test desc
    >>> reciprocal.required
    False
    >>> reciprocal.readonly
    True


Test the default accepted media type
------------------------------------

Named file::

    >>> field = NamedFile()
    >>> field.accept
    ()
    >>> fieldType = IFieldNameExtractor(field)()
    >>> handler = getUtility(IFieldExportImportHandler, name=fieldType)
    >>> element = handler.write(field, u'dummy', fieldType)
    >>> print(prettyXML(element))
    <field name="dummy" type="plone.namedfile.field.NamedFile"/>

    >>> element__ = etree.XML("""\
    ... <field name="dummy" type="plone.namedfile.field.NamedFile"/>
    ... """)

    >>> reciprocal__ = handler.read(element__)
    >>> reciprocal__.accept
    ()


Named image::

    >>> field = NamedImage()
    >>> field.accept
    ('image/*',)
    >>> fieldType = IFieldNameExtractor(field)()
    >>> handler = getUtility(IFieldExportImportHandler, name=fieldType)
    >>> element = handler.write(field, u'dummy', fieldType)
    >>> print(prettyXML(element))
    <field name="dummy" type="plone.namedfile.field.NamedImage"/>

    >>> element = etree.XML("""\
    ... <field type="plone.namedfile.field.NamedImage"/>
    ... """)

    >>> reciprocal = handler.read(element)
    >>> reciprocal.accept
    ('image/*',)


Named blob file::

    >>> field = NamedBlobFile()
    >>> field.accept
    ()
    >>> fieldType = IFieldNameExtractor(field)()
    >>> handler = getUtility(IFieldExportImportHandler, name=fieldType)
    >>> element = handler.write(field, u'dummy', fieldType)
    >>> print(prettyXML(element))
    <field name="dummy" type="plone.namedfile.field.NamedBlobFile"/>

    >>> element = etree.XML("""\
    ... <field type="plone.namedfile.field.NamedBlobFile"/>
    ... """)

    >>> reciprocal = handler.read(element)
    >>> reciprocal.accept
    ()


Named blob image::

    >>> field = NamedBlobImage()
    >>> field.accept
    ('image/*',)
    >>> fieldType = IFieldNameExtractor(field)()
    >>> handler = getUtility(IFieldExportImportHandler, name=fieldType)
    >>> element = handler.write(field, u'dummy', fieldType)
    >>> print(prettyXML(element))
    <field name="dummy" type="plone.namedfile.field.NamedBlobImage"/>

    >>> element = etree.XML("""\
    ... <field type="plone.namedfile.field.NamedBlobImage"/>
    ... """)

    >>> reciprocal = handler.read(element)
    >>> reciprocal.accept
    ('image/*',)

