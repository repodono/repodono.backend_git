# -*- coding: utf-8 -*-
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import repodono.backend.git


class RepodonoBackendGitLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        self.loadZCML(package=repodono.backend.git)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'repodono.backend.git:default')


REPODONO_BACKEND_GIT_FIXTURE = RepodonoBackendGitLayer()


REPODONO_BACKEND_GIT_INTEGRATION_TESTING = IntegrationTesting(
    bases=(REPODONO_BACKEND_GIT_FIXTURE,),
    name='RepodonoBackendGitLayer:IntegrationTesting'
)


REPODONO_BACKEND_GIT_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(REPODONO_BACKEND_GIT_FIXTURE,),
    name='RepodonoBackendGitLayer:FunctionalTesting'
)


REPODONO_BACKEND_GIT_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        REPODONO_BACKEND_GIT_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE
    ),
    name='RepodonoBackendGitLayer:AcceptanceTesting'
)
