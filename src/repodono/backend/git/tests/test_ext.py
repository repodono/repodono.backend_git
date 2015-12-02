# -*- coding: utf-8 -*-
import unittest

from repodono.backend.git import ext


class ParseGitModuleTestCase(unittest.TestCase):

    def test_empty(self):
        result = ext.parse_gitmodules('')
        self.assertEqual(result, {})

    def test_basic(self):
        text = (
            '[submodule "dummy"]\n'
            '  path = dummy\n'
            '  url = http://example.com/dummy/.git\n'
        )

        result = ext.parse_gitmodules(text)
        self.assertEqual(result, {'dummy': 'http://example.com/dummy/.git'})

    def test_multiple(self):
        text = (
            '[submodule "foo"]\n'
            '  path = foo\n'
            '  url = http://example.com/foo/.git\n'
            '\n'
            '[submodule "bar"]\n'
            '  path = bar\n'
            '  url = http://example.com/bar/.git\n'
        )

        result = ext.parse_gitmodules(text)
        self.assertEqual(result, {
            'foo': 'http://example.com/foo/.git',
            'bar': 'http://example.com/bar/.git',
        })

    def test_malformed_missing_submodule(self):
        text = (
            '[submodule "foo"]\n'
            '  path = foo\n'
            '  url = http://example.com/foo/.git\n'
            'submodule "bar"]\n'
            '  path = bar\n'
            '  url = http://example.com/bar/.git\n'
            '\n'
            '[submodule "baz"]\n'
            '  path = baz=baz\n'
            '  url = http://example.com/baz/.git\n'
        )

        result = ext.parse_gitmodules(text)
        self.assertEqual(result, {
            # only the first declaration survives
            'foo': 'http://example.com/foo/.git',
            'baz=baz': 'http://example.com/baz/.git',
        })
