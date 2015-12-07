# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from repodono.backend.git.testing import REPODONO_BACKEND_GIT_INTEGRATION_TESTING  # noqa
from plone import api

import unittest2 as unittest


class TestSetup(unittest.TestCase):
    """Test that repodono.backend.git is properly installed."""

    layer = REPODONO_BACKEND_GIT_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """
        Test if repodono.backend.git is installed with portal_quickinstaller.
        """
        self.assertTrue(
            self.installer.isProductInstalled('repodono.backend.git'))

    def test_browserlayer(self):
        """Test that IRepodonoBackendGitLayer is registered."""
        from repodono.backend.git.interfaces import IRepodonoBackendGitLayer
        from plone.browserlayer import utils
        self.assertIn(IRepodonoBackendGitLayer, utils.registered_layers())

    def test_storage_utility_registry(self):
        """Test the git term is added to utility registry."""
        from plone.registry.interfaces import IRegistry
        from zope.component import getUtility
        registry = getUtility(IRegistry)
        self.assertIn('git', registry['repodono.storage.backends'])


class TestUninstall(unittest.TestCase):

    layer = REPODONO_BACKEND_GIT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.uninstallProducts(['repodono.backend.git'])

    def test_product_uninstalled(self):
        """Test if repodono.backend.git is cleanly uninstalled."""
        self.assertFalse(
            self.installer.isProductInstalled('repodono.backend.git'))

    def test_browserlayer_removed(self):
        """Test that IRepodonoStorageLayer is removed."""
        from repodono.backend.git.interfaces import IRepodonoBackendGitLayer
        from plone.browserlayer import utils
        self.assertNotIn(IRepodonoBackendGitLayer, utils.registered_layers())

    def test_storage_utility_registry(self):
        """Test the git term is removed from utility registry."""
        from plone.registry.interfaces import IRegistry
        from zope.component import getUtility
        registry = getUtility(IRegistry)
        self.assertNotIn('git', registry['repodono.storage.backends'])
