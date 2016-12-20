# -*- coding: utf-8 -*-
from plone.testing import Layer
from plone.testing import publisher
from plone.testing import z2
from plone.testing import zca
from plone.testing import zodb
from zope.configuration import xmlconfig


class NamedFileTestLayer(Layer):

    defaultBases = (z2.STARTUP, publisher.PUBLISHER_DIRECTIVES)

    def setUp(self):
        zca.pushGlobalRegistry()

        import plone.namedfile
        xmlconfig.file('testing.zcml', plone.namedfile)

        self['zodbDB'] = zodb.stackDemoStorage(
            self.get('zodbDB'),
            name='NamedFileFixture'
        )

    def tearDown(self):
        # Zap the stacked ZODB
        self['zodbDB'].close()
        del self['zodbDB']

        # Zap the stacked zca context
        zca.popGlobalRegistry()


PLONE_NAMEDFILE_FIXTURE = NamedFileTestLayer()

PLONE_NAMEDFILE_INTEGRATION_TESTING = z2.IntegrationTesting(
    bases=(PLONE_NAMEDFILE_FIXTURE, ),
    name='plone.namedfile:NamedFileTestLayerIntegration',
)

PLONE_NAMEDFILE_FUNCTIONAL_TESTING = z2.FunctionalTesting(
    bases=(PLONE_NAMEDFILE_FIXTURE, ),
    name='plone.namedfile:NamedFileTestLayerFunctional',
)
