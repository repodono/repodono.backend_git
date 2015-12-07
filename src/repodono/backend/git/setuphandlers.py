# -*- coding: utf-8 -*-
from zope.component import getUtility
from repodono.registry.interfaces import IUtilityRegistry


def post_install(context):
    """Post install script"""
    if context.readDataFile('repodonobackendgit_default.txt') is None:
        return

    utilities = getUtility(IUtilityRegistry, 'repodono.storage.backends')
    utilities.enable('git')


def uninstall(context):
    """Uninstall script"""
    if context.readDataFile('repodonobackendgit_uninstall.txt') is None:
        return

    utilities = getUtility(IUtilityRegistry, 'repodono.storage.backends')
    utilities.disable('git')
