# -*- coding: utf-8 -*-
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer


class NamedFileTestLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import plone.namedfile
        self.loadZCML(package=plone.namedfile, name="testing.zcml")

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'plone.outputfilters:default')


PLONE_NAMEDFILE_FIXTURE = NamedFileTestLayer()

PLONE_NAMEDFILE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PLONE_NAMEDFILE_FIXTURE, ),
    name='plone.namedfile:Integration',
)

PLONE_NAMEDFILE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLONE_NAMEDFILE_FIXTURE, ),
    name='plone.namedfile:Functional',
)
