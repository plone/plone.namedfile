from plone.testing import Layer
from plone.testing import publisher
from plone.testing import zca
from plone.testing import zope
from zope.configuration import xmlconfig


class NamedFileTestLayer(Layer):

    defaultBases = (zope.STARTUP, publisher.PUBLISHER_DIRECTIVES)

    def setUp(self):
        zca.pushGlobalRegistry()

        import plone.namedfile

        xmlconfig.file("testing.zcml", plone.namedfile)

    def tearDown(self):
        # Zap the stacked zca context
        zca.popGlobalRegistry()


PLONE_NAMEDFILE_FIXTURE = NamedFileTestLayer()

PLONE_NAMEDFILE_INTEGRATION_TESTING = zope.IntegrationTesting(
    bases=(PLONE_NAMEDFILE_FIXTURE,),
    name="plone.namedfile:NamedFileTestLayerIntegration",
)

PLONE_NAMEDFILE_FUNCTIONAL_TESTING = zope.FunctionalTesting(
    bases=(PLONE_NAMEDFILE_FIXTURE,),
    name="plone.namedfile:NamedFileTestLayerFunctional",
)
