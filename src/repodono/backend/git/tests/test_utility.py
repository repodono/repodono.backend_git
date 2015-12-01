# -*- coding: utf-8 -*-
import unittest
import tempfile
import shutil
import os
from os.path import basename, dirname, join, isdir
from cStringIO import StringIO
import threading

from pygit2 import init_repository
from dulwich.repo import Repo
from dulwich.server import DictBackend
from dulwich.server import TCPGitServer
from dulwich.tests.compat.test_client import HTTPGitServer

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

from repodono.backend.git.testing import util


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
        self.assertEqual(storage.shortrev, revs[-1][:12])

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

        with self.assertRaises(PathNotFoundError):
            storage.pathinfo('nested/deep/nosuchpath')

        with self.assertRaises(PathNotFoundError):
            storage.listdir('nested/deep/nosuchpath')

        with self.assertRaises(PathNotDirError):
            storage.listdir('nested/deep/dir/file')

        with self.assertRaises(PathNotFileError):
            storage.file('nested/deep/dir')

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

        with self.assertRaises(PathNotFoundError):
            # normally won't be traversed, but for completeness, test
            # that getting an object with a type that is not expected
            # should fail.
            storage._get_obj('file1', DummyItem)

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

        result = storage.log(None, 1)
        self.assertEqual(result, [])

        self.assertEqual(storage.shortrev, None)
        self.assertEqual(storage.rev, None)

    def test_011_storage_empty_failures(self):
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

        with self.assertRaises(RevisionNotFoundError):
            storage.log('nosuchrev', 1)

    def test_100_storage_repodata(self):
        # a simple test to check that repodata is available.
        util.extract_archive(self.testdir)
        repodata = DummyItem(join(self.testdir, 'repodata'))
        storage = GitStorage(repodata)

        pathinfo = storage.pathinfo('1')
        self.assertEqual(pathinfo, {
            'basename': '1',
            'date': '',
            'size': 0,
            'type': 'folder',
        })

    def test_110_storage_subrepo_default(self):
        # a simple test to check that repodata is available.
        util.extract_archive(self.testdir)
        repodata = DummyItem(join(self.testdir, 'repodata'))
        storage = GitStorage(repodata)
        pathinfo = storage.pathinfo('ext/import1')
        self.assertEqual(pathinfo, {
            'basename': 'import1',
            'date': '',
            'size': 0,
            'type': 'subrepo',
            'obj': {
                '': '_subrepo',
                'location': 'http://models.example.com/w/import1',
                'path': '',
                'rev': '466b6256bd9a1588256558a8e644f04b13bc04f3',
            },
        })

        with self.assertRaises(PathNotFileError):
            storage.file('ext/import1')

        with self.assertRaises(PathNotDirError):
            storage.listdir('ext/import1')

    def test_110_storage_subrepo_alt_revision(self):
        # a simple test to check that repodata is available.
        util.extract_archive(self.testdir)
        repodata = DummyItem(join(self.testdir, 'repodata'))
        storage = GitStorage(repodata)
        # checkout a specific rev
        storage.checkout(util.ARCHIVE_REVS[1])
        pathinfo = storage.pathinfo('ext/import1')
        self.assertEqual(pathinfo, {
            'basename': 'import1',
            'date': '',
            'size': 0,
            'type': 'subrepo',
            'obj': {
                '': '_subrepo',
                'location': 'http://models.example.com/w/import1',
                'path': '',
                'rev': '00cf337ef94f882f2585684c1c5c601285312f85',
            },
        })


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

    def test_base_failure(self):
        item = DummyItem(self.testdir)
        with self.assertRaises(PathNotFoundError):
            storage = GitStorage(item)

        with self.assertRaises(PathNotFoundError):
            self.backend.acquire(item)

    def test_install(self):
        item = DummyItem(self.testdir)
        self.backend.install(item)
        storage = self.backend.acquire(item)
        self.assertTrue(isinstance(storage, GitStorage))
        self.assertEqual(storage.listdir(''), [])

    def test_sync_identifier(self):
        util.extract_archive(self.testdir)
        simple1_path = join(self.testdir, 'simple1')
        simple2_path = join(self.testdir, 'simple2')

        simple1 = DummyItem(simple1_path)
        simple2 = DummyItem(simple2_path)
        storage1 = self.backend.acquire(simple1)
        storage2 = self.backend.acquire(simple2)
        self.assertEqual(storage1.files(), [
            'README', 'test1', 'test2', 'test3'])
        self.assertEqual(storage2.files(), [
            'test1', 'test2', 'test3'])

        self.backend._sync_identifier(simple2_path, simple1_path)
        storage2 = self.backend.acquire(simple2)
        self.assertEqual(storage2.files(), [
            'README', 'test1', 'test2', 'test3'])

    def test_sync_git_server(self):
        util.extract_archive(self.testdir)
        simple1_path = join(self.testdir, 'simple1')
        simple2_path = join(self.testdir, 'simple2')
        simple2 = DummyItem(simple2_path)

        dulwich_repo = Repo(simple1_path)
        dulwich_backend = DictBackend({b'/': dulwich_repo})
        dulwich_server = TCPGitServer(dulwich_backend, b'localhost', 0)
        self.addCleanup(dulwich_server.shutdown)
        self.addCleanup(dulwich_server.server_close)
        threading.Thread(target=dulwich_server.serve).start()
        _, port = dulwich_server.socket.getsockname()

        self.backend._sync_identifier(
            simple2_path, 'git://localhost:%d' % port)

        storage2 = self.backend.acquire(simple2)
        self.assertEqual(storage2.files(), [
            'README', 'test1', 'test2', 'test3'])

    def test_sync_http_identifier(self):
        util.extract_archive(self.testdir)
        simple1_path = join(self.testdir, 'simple1')
        simple2_path = join(self.testdir, 'simple2')

        simple2 = DummyItem(simple2_path)
        storage2 = self.backend.acquire(simple2)
        self.assertEqual(storage2.files(), ['test1', 'test2', 'test3'])

        self._httpd = HTTPGitServer(("localhost", 0), simple1_path)
        self.addCleanup(self._httpd.shutdown)
        threading.Thread(target=self._httpd.serve_forever).start()

        self.backend._sync_identifier(simple2_path, self._httpd.get_url())

        storage2 = self.backend.acquire(simple2)
        self.assertEqual(storage2.files(), [
            'README', 'test1', 'test2', 'test3'])
