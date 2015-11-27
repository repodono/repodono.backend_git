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

from repodono.storage.interfaces import IStorageBackendFSAdapter
from repodono.storage.interfaces import IStorageInfo
from repodono.storage.exceptions import PathNotDirError
from repodono.storage.exceptions import PathNotFileError
from repodono.storage.exceptions import PathNotFoundError
from repodono.storage.exceptions import RevisionNotFoundError

from repodono.backend.git.utility import GitStorage
from repodono.backend.git.utility import GitStorageBackend
from repodono.backend.git.tests import util


class DummyFSBackendAdapter(object):

    def __init__(self, backend, context):
        self.backend = backend
        self.context = context

    def install(self):
        pass

    def acquire(self):
        return self.context.path


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

    def test_000_fail_repo(self):
        item = DummyItem(self.testdir)
        with self.assertRaises(PathNotFoundError):
            storage = GitStorage(item)

    def test_010_storage_base(self):
        item = DummyItem(self.testdir)
        revs, fulllist = util.create_demo_git_repo(self.testdir)

        storage = GitStorage(item)
        result = storage.files()
        self.assertEqual(result, fulllist)
        entries = storage.listdir('')
        self.assertEqual(entries, ['file1', 'file2', 'file3', 'nested'])

        self.assertEqual(storage.rev, revs[-1])

        info = storage.pathinfo('nested')
        self.assertEqual(info['size'], 0)
        self.assertEqual(info['type'], 'folder')

        entries = storage.listdir('nested')
        self.assertEqual(entries, ['deep'])

        info = storage.pathinfo('file1')
        self.assertEqual(info['size'], 38)
        self.assertEqual(info['type'], 'file')

        with self.assertRaises(PathNotFoundError):
            storage.pathinfo('nosuchpath')

        with self.assertRaises(PathNotFoundError):
            storage.listdir('nosuchpath')

        with self.assertRaises(PathNotDirError):
            storage.listdir('file1')

        with self.assertRaises(PathNotFileError):
            storage.file('nested')

        logs = storage.log('HEAD', 10)
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0]['author'], u'user3')
        self.assertEqual(logs[1]['author'], u'user3')
        self.assertEqual(logs[2]['author'], u'user2')
        self.assertEqual(logs[3]['author'], u'user1')

        logs = storage.log(None, 2)
        self.assertEqual(len(logs), 2)

        storage.checkout(revs[0])
        self.assertEqual(storage.rev, revs[0])

    def test_011_storage_empty_basic(self):
        emptydir = join(self.testdir, 'empty')

        repo = init_repository(join(emptydir, '.git'), bare=True)

        item = DummyItem(emptydir)
        storage = GitStorage(item)
        self.assertEqual(storage.files(), [])

        pathinfo = storage.pathinfo('')
        self.assertEqual(pathinfo, {
            'basename': '',
            'date': '',
            'size': 0,
            'type': 'folder',
        })

        result = list(storage.listdir(''))
        self.assertEqual(result, [])

        self.assertEqual(storage.shortrev, None)
        self.assertEqual(storage.rev, None)

    def test_011_storage_empty_failurse(self):
        emptydir = join(self.testdir, 'empty')
        repo = init_repository(join(emptydir, '.git'), bare=True)
        item = DummyItem(emptydir)
        storage = GitStorage(item)

        pathinfo = storage.pathinfo('')

        with self.assertRaises(RevisionNotFoundError):
            storage.checkout('nowhere')

        pathinfo = storage.pathinfo('')
        self.assertEqual(pathinfo, {
            'basename': '',
            'date': '',
            'size': 0,
            'type': 'folder',
        })

        with self.assertRaises(PathNotFoundError):
            storage.listdir('nowhere')


class StorageBackendTestCase(unittest.TestCase):

    def setUp(self):
        self.backend = GitStorageBackend()
        self.testdir = tempfile.mkdtemp()
        zope.component.provideAdapter(DummyStorageInfo, (DummyItem,))
        zope.component.provideAdapter(
            DummyFSBackendAdapter,
            (GitStorageBackend, DummyItem,),
            IStorageBackendFSAdapter,
        )

    def tearDown(self):
        shutil.rmtree(self.testdir)
        clearZCML()

    def test_base(self):
        item = DummyItem(self.testdir)
        with self.assertRaises(PathNotFoundError):
            storage = GitStorage(item)

        with self.assertRaises(PathNotFoundError):
            self.backend.acquire(item)

        self.backend.install(item)
        storage = self.backend.acquire(item)
        self.assertTrue(isinstance(storage, GitStorage))
