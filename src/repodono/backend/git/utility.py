# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.tz import tzoffset
from logging import getLogger
from glob import glob
from os.path import join
from os import walk
import json
# import mimetypes

from zope.component import getMultiAdapter
import zope.interface

from pygit2 import Signature
from pygit2 import Repository
from pygit2 import Tree
from pygit2 import Blob
from pygit2 import Tag
from pygit2 import Commit
from pygit2 import discover_repository, init_repository
from pygit2 import GIT_SORT_TIME

from dulwich.repo import Repo
from dulwich.client import HttpGitClient

from .ext import parse_gitmodules
# from .interfaces import IGitWorkspace

from repodono.storage.base import BaseStorageBackend
from repodono.storage.base import BaseStorage
from repodono.storage.interfaces import IStorageInfo
from repodono.storage.interfaces import IStorageBackendFSAdapter
from repodono.storage.exceptions import PathNotDirError
from repodono.storage.exceptions import PathNotFileError
from repodono.storage.exceptions import PathNotFoundError
from repodono.storage.exceptions import RevisionNotFoundError
from repodono.storage.exceptions import StorageNotFoundError

logger = getLogger(__name__)

GIT_MODULE_FILE = '.gitmodules'


def rfc2822(committer):
    return datetime.fromtimestamp(committer.time,
        tzoffset(None, committer.offset * 60))


class GitStorageBackend(BaseStorageBackend):
    """
    Git Storage Backend
    """

    title = u'Git'
    command = u'git'
    clone_verb = u'clone'

    def __init__(self):
        pass

    def acquire(self, context):
        fshelper = getMultiAdapter((self, context), IStorageBackendFSAdapter)
        # This is simply validation.  Storage instance uses IStorageInfo
        fshelper.acquire()
        return GitStorage(context)

    def install(self, context):
        fshelper = getMultiAdapter((self, context), IStorageBackendFSAdapter)
        rp = fshelper.acquire()
        self._create(rp)
        # Also tag the object with our custom interface?
        # zope.interface.alsoProvides(context, IGitStorage)

    def _create(self, rp):
        repo = init_repository(join(rp, '.git'), bare=True)
        # Allow receivepack by default for git push.
        repo.config.set_multivar('http.receivepack', '', 'true')

    def _sync_identifier(self, context, identifier):
        # XXX assuming master.
        branch_name = 'master'
        # XXX when we figure out how to let users pick their primary
        # branches, use what they specify instead.
        branch = "refs/heads/%s" % branch_name

        # Since the network and remote handling aspect between dulwich
        # and pygit2 have different strengths, i.e. dulwich has better
        # remote network handling and fetching without having to create
        # a named remote, and pygit2 for determining merge base for
        # fast-forwarding the local to remote if applicable.

        # Process starts with dulwich.
        # 0. Connect to remote
        # 1. Fetch content
        # 2. Acquire merge target pairs.

        merge_target = self._fetch(rp, identifier, branch)

        # Then use pygit2.
        # 3. If merge base between the two have diverted, abort.
        # 4. If remote is fresher, fast forward local.

        return self._fast_forward(rp, merge_target, branch)

    def _fetch(self, local_path, remote_id, branch):
        # dulwich repo
        local = Repo(local_path)

        # Determine the fetch strategy based on protocol.
        if remote_id.startswith('http'):
            root, frag = remote_id.rsplit('/', 1)
            client = HttpGitClient(root)
            try:
                remote_refs = client.fetch(frag, local)
            except:
                raise ValueError('error fetching from remote: %s' % remote_id)
        elif remote_id.startswith('/'):
            client = Repo(remote_id)
            remote_refs = client.fetch(local)
        else:
            raise ValueError('remote not supported: %s' % remote_id)

        if branch in remote_refs:
            merge_target = remote_refs[branch]
        else:
            # Unknown, fall back to HEAD.
            merge_target = remote_refs['HEAD']

        # Switch usage to libgit2/pygit2 repo for "merging".

        return merge_target

    def _fast_forward(self, local_path, merge_target, branch):
        # pygit2 repo
        repo = Repository(discover_repository(local_path))

        # convert merge_target from hex into oid.
        fetch_head = repo.revparse_single(merge_target)

        # try to resolve a common anscestor between fetched and local
        try:
            head = repo.revparse_single(branch)
        except:
            # New repo, create the reference now and finish.
            repo.create_reference(branch, fetch_head.oid)
            return True, 'Created new branch: %s' % branch

        if head.oid == fetch_head.oid:
            return True, 'Source and target are identical.'

        # raises KeyError if no merge bases found.
        oid = repo.merge_base(head.oid, fetch_head.oid)

        # Three different outcomes between the remaining cases.
        if oid.hex not in (head.oid.hex, fetch_head.oid.hex):
            # common ancestor is beyond both of these, not going to
            # attempt a merge here and will assume this:
            raise ValueError('heads will diverge.')
        elif oid.hex == fetch_head.oid.hex:
            # Remote is the common base, so nothing to do.
            return True, 'No new changes found.'

        # This case remains: oid.hex == head.oid.hex
        # Local is the common base, so remote is newer, fast-forward.
        try:
            ref = repo.lookup_reference(branch)
            ref.delete()
        except KeyError:
            # assume repo is empty.
            pass

        repo.create_reference(branch, fetch_head.oid)

        return True, 'Fast-forwarded branch: %s' % branch


class GitStorage(BaseStorage):

    _backend = None

    def __init__(self, context, repo_path=None):
        self.context = context
        rp = IStorageInfo(context).path

        try:
            self.repo = Repository(discover_repository(rp))
        except KeyError:
            # discover_repository may have failed.
            raise PathNotFoundError('repository does not exist at path')

        self.checkout()  # defaults to HEAD.

    @property
    def empty_root(self):
        return {'': '_empty_root'}

    def _get_empty_root(self):
        return self.empty_root

    def _get_obj(self, path, cls=None):
        if path == '' and self._commit is None:
            # special case
            return self._get_empty_root()

        if self._commit is None:
            raise PathNotFoundError('repository is empty')

        root = self._commit.tree
        try:
            breadcrumbs = []
            fragments = list(reversed(path.split('/')))
            node = root
            oid = None
            while fragments:
                fragment = fragments.pop()
                if not fragment == '':
                    # no empty string entries, also skips over '//' and
                    # leaves the final node (if directory) as the tree.
                    oid = node[fragment].oid
                    node = self.repo.get(oid)
                breadcrumbs.append(fragment)
                if node is None:
                    # strange.  Looks like it's either submodules only
                    # have entry nodes or pygit2 doesn't fully support
                    # this.  Try to manually resolve the .gitmodules
                    # file.
                    if not cls == Blob:
                        # If we want a file, forget it.
                        submods = parse_gitmodules(self.repo.get(
                            root[GIT_MODULE_FILE].oid).data)
                        submod = submods.get('/'.join(breadcrumbs))
                        if submod:
                            fragments.reverse()
                            return {
                                '': '_subrepo',
                                'location': submod,
                                'path': '/'.join(fragments),
                                'rev': oid.hex,
                            }
                    raise PathNotDirError('path not dir')

            if cls is None or isinstance(node, cls):
                return node
        except KeyError:
              # can't find what is needed in repo, raised by pygit2
            raise PathNotFoundError('path not found')

        # not what we were looking for.
        if cls == Tree:
            raise PathNotDirError('path not dir')
        elif cls == Blob:
            raise PathNotFileError('path not file')
        raise PathNotFoundError('path not found')

    @property
    def _commit(self):
        return self.__commit

    @property
    def rev(self):
        if self.__commit:
            return self.__commit.hex
        return None

    @property
    def shortrev(self):
        # TODO this is an interim solution.
        if self.rev:
            return self.rev[:12]

    def basename(self, name):
        return name.split('/')[-1]

    def checkout(self, rev=None):
        # None maps to the default revision.
        if rev is None:
            rev = 'HEAD'

        try:
            self.__commit = self.repo.revparse_single(rev)
        except KeyError:
            if rev == 'HEAD':
                # probably a new repo.
                self.__commit = None
                return
            raise RevisionNotFoundError('revision %s not found' % rev)
            # otherwise a RevisionNotFoundError should be raised.

    def files(self):
        def _files(tree, current_path=None):
            results = []
            for node in tree:
                if current_path:
                    name = '/'.join([current_path, node.name])
                else:
                    name = node.name

                obj = self.repo.get(node.oid)
                if isinstance(obj, Blob):
                    results.append(name)
                elif isinstance(obj, Tree):
                    results.extend(_files(obj, name))
            return results

        if not self._commit:
            return []
        results = _files(self._commit.tree)
        return results

    def file(self, path):
        return self._get_obj(path, Blob).data

    def listdir(self, path):
        if path:
            tree = self._get_obj(path, Tree)
        else:
            if self._commit is None:
                return []
            tree = self._commit.tree

        return [entry.name for entry in tree]

    def format(self, **kw):
        # XXX backwards compatibility??
        return kw

    def log(self, start, count, branch=None, shortlog=False):
        """
        start and branch are literally the same thing.
        """

        def _log(iterator):
            for pos, commit in iterator:
                if pos == count:
                    raise StopIteration
                yield {
                    'author': commit.committer.name,
                    'email': self._commit.committer.email,
                    'date': rfc2822(commit.committer).date(),
                    'node': commit.hex,
                    'rev': commit.hex,
                    'desc': commit.message
                }

        if start is None:
            # assumption.
            start = 'HEAD'
            try:
                self.repo.revparse_single(start)
            except KeyError:
                return []

        try:
            rev = self.repo.revparse_single(start).hex
        except KeyError:
            raise RevisionNotFoundError('revision %s not found' % start)

        iterator = enumerate(self.repo.walk(rev, GIT_SORT_TIME))

        return list(_log(iterator))

    def pathinfo(self, path):
        obj = self._get_obj(path)
        if isinstance(obj, Blob):
            return self.format(**{
                'type': 'file',
                'basename': self.basename(path),
                'size': obj.size,
                'date': rfc2822(self._commit.committer),
            })
        elif isinstance(obj, dict):
            # special cases are represented as dict.
            if obj[''] == '_subrepo':
                return self.format(**{
                    'type': 'subrepo',
                    'date': '',
                    'size': 0,
                    'basename': self.basename(path),
                    # extra field.
                    'obj': obj,
                })

            elif obj[''] == '_empty_root':
                return self.format(**{
                    'type': 'folder',
                    'date': '',
                    'size': 0,
                    'basename': self.basename(path),
                })

        # Assume this is a Tree.
        return self.format(**{
            'basename': self.basename(path),
            'size': 0,
            'type': 'folder',
            'date': '',
        })
