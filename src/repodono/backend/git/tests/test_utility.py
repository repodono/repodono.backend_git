# -*- coding: utf-8 -*-
import unittest
import tempfile
import shutil
import os
from os.path import basename, dirname, join, isdir
from cStringIO import StringIO

from pygit2 import init_repository

import zope.component
import zope.interface
from zope.component.hooks import getSiteManager

from zope.configuration.xmlconfig import xmlconfig
from zope.component.tests import clearZCML

from repodono.storage.interfaces import IStorageInfo

from repodono.backend.git.utility import GitStorage
from repodono.backend.git.utility import GitStorageBackend
from repodono.backend.git.tests import util


class DummyItem(object):
    def __init__(self, path):
        self.path = path


@zope.interface.implementer(IStorageInfo)
class DummyStorageInfo(object):

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        return self.context.path


class StorageTestCase(unittest.TestCase):

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        zope.component.provideAdapter(DummyStorageInfo, (DummyItem,))

    def tearDown(self):
        shutil.rmtree(self.testdir)
        clearZCML()

    def test_010_storage_base(self):
        item = DummyItem(self.testdir)
        revs, fulllist = util.create_demo_git_repo(self.testdir)

        storage = GitStorage(item)
        result = storage.files()
        self.assertEqual(result, fulllist)
        entries = storage.listdir('')
        self.assertEqual(entries, ['file1', 'file2', 'file3', 'nested'])

        entries = storage.listdir('nested')
        self.assertEqual(entries, ['deep'])

        info = storage.pathinfo('file1')
        self.assertEqual(info['size'], 38)
        self.assertEqual(info['type'], 'file')

    def test_011_storage_empty_checkout(self):
        emptydir = join(self.testdir, 'empty')

        repo = init_repository(join(emptydir, '.git'), bare=True)

        item = DummyItem(emptydir)
        storage = GitStorage(item)
        self.assertEqual(storage.files(), [])

        pathinfo = storage.pathinfo('')
        self.assertEqual(pathinfo, {
            'basename': '',
            'date': '',
            'size': '',
            'type': 'folder',
        })

        result = list(storage.listdir(''))
        self.assertEqual(result, [])

        self.assertEqual(storage.shortrev, None)
        self.assertEqual(storage.rev, None)
