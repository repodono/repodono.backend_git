# -*- coding: utf-8 -*-
from cStringIO import StringIO
from os.path import join
from os.path import dirname
import tarfile
from time import time

from pygit2 import Repository
from pygit2 import init_repository
from pygit2 import Signature
from pygit2 import GIT_FILEMODE_BLOB
from pygit2 import GIT_FILEMODE_TREE

ARCHIVE_NAME = 'repodata.tgz'
ARCHIVE_PATH = join(dirname(__file__), ARCHIVE_NAME)
ARCHIVE_REVS = [
    '42a9021e2e4df151c3255b5429899f421b0c3431',
    '67e07ebc8b3a0c646f4a9f898c543ad1a56e1fb8',
    '0a6808653e657eac20d447cf36022010bdbd3253',
    '090ab454beca05a8ab5b5e9bd15c06eaba790a8a',
    '93c2615285898ffaf4ea81611e54a64c99a157cb',
    '0358f183cc3ede11a357a807c80218f74fa4a539',
    'c9de8a045ef5d352441d69b630f924f12d621a77',
    'eab05fccc349fbeb57ade09a197ddc72cd9e4388',
]


def extract_archive(path, archive_path=ARCHIVE_PATH):
    # extraction 
    tf = tarfile.open(archive_path, 'r:gz')
    mem = tf.getmembers()
    for m in mem:
        tf.extract(m, path)
    tf.close()


def create_demo_git_repo(repodir):
    # For the unit test - this essentially verifies that pygit2 is
    # available for usage.
    revs = []

    nested_name = 'nested/deep/dir/file'
    nested_file = 'This is\n\na deeply nested file\n'
    files = [
        'This is a test file.\n',
        'This is a test file.\nWith a new line.\n',
        'This is a test file.\nWith a different new line.\n',
    ]
    msg = 'added some files'
    user = 'Tester'
    email = '<test@example.com>'

    # For standard/uniqueness, repo place under `.git`.
    repo = init_repository(join(repodir, '.git'), bare=True)
    tbder = repo.TreeBuilder()

    tbder.insert('file1', repo.create_blob(files[0]),
        GIT_FILEMODE_BLOB)
    tbder.insert('file2', repo.create_blob(files[0]),
        GIT_FILEMODE_BLOB)
    commit = repo.create_commit('refs/heads/master',
        Signature('user1', '1@example.com', int(time()), 0),
        Signature('user1', '1@example.com', int(time()), 0),
        'added1', tbder.write(),
        [],
    )
    revs.append(commit.hex)

    tbder.insert('file1', repo.create_blob(files[1]),
        GIT_FILEMODE_BLOB)
    commit = repo.create_commit('refs/heads/master',
        Signature('user2', '2@example.com', int(time()), 0),
        Signature('user2', '2@example.com', int(time()), 0),
        'added2', tbder.write(),
        [revs[-1]],
    )
    revs.append(commit.hex)

    tbder.insert('file2', repo.create_blob(files[1]),
        GIT_FILEMODE_BLOB)
    tbder.insert('file3', repo.create_blob(files[0]),
        GIT_FILEMODE_BLOB)
    commit = repo.create_commit('refs/heads/master',
        Signature('user3', '3@example.com', int(time()), 0),
        Signature('user3', '3@example.com', int(time()), 0),
        'added3', tbder.write(),
        [revs[-1]],
    )
    revs.append(commit.hex)

    ntbder = repo.TreeBuilder()
    nnames = nested_name.split('/')
    ntbder.insert(nnames.pop(), repo.create_blob(nested_file),
        GIT_FILEMODE_BLOB)

    for n in reversed(nnames):
        ntree = ntbder.write()
        ntbder = repo.TreeBuilder()
        ntbder.insert(n, ntree, GIT_FILEMODE_TREE)

    # ntree is the final node, n is leftover from the iterator,
    # ntbder is extra and is ignored.
    tbder.insert(n, ntree, GIT_FILEMODE_TREE)
    commit = repo.create_commit('refs/heads/master',
        Signature('user3', '3@example.com', int(time()), 0),
        Signature('user3', '3@example.com', int(time()), 0),
        'added4', tbder.write(),
        [revs[-1]],
    )
    revs.append(commit.hex)

    fulllist = ['file1', 'file2', 'file3', nested_name]

    # latest rev is revs[-1]
    return revs, fulllist
