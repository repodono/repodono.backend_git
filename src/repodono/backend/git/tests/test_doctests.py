# -*- coding: utf-8 -*-
from plone.testing import layered
import doctest
import unittest

from repodono.backend.git.testing import (
    REPODONO_BACKEND_GIT_FUNCTIONAL_TESTING,
)


tests = (
    'integration.rst',
)


def test_suite():
    t = [layered(doctest.DocFileSuite(f, optionflags=doctest.ELLIPSIS),
         layer=REPODONO_BACKEND_GIT_FUNCTIONAL_TESTING)
         for f in tests]
    return unittest.TestSuite(t)
