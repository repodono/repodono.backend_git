Git Storage Integration
=======================

Make up a storage_enabled content type::

    >>> portal = layer['portal']
    >>> from plone.dexterity.fti import DexterityFTI
    >>> fti = DexterityFTI('storage_enabled')
    >>> fti.klass = 'plone.dexterity.content.Item'
    >>> fti.behaviors = ('repodono.storage.behavior.storage.IStorageEnabler',)
    >>> portal.portal_types._setObject('storage_enabled', fti)
    'storage_enabled'

Setup a test browser::

    >>> from plone.app.testing import TEST_USER_ID, TEST_USER_NAME
    >>> from plone.app.testing import TEST_USER_PASSWORD, setRoles
    >>> setRoles(portal, TEST_USER_ID, ['Manager'])
    >>> import transaction; transaction.commit()
    >>> from plone.testing.z2 import Browser
    >>> browser = Browser(layer['app'])
    >>> browser.addHeader('Authorization', 'Basic %s:%s' %
    ...     (TEST_USER_NAME, TEST_USER_PASSWORD,))

See that the git option is available::

    >>> browser.open('http://nohost/plone/++add++storage_enabled')
    >>> backends = browser.getControl('Backend')
    >>> backends.options
    ['git']

Now add the storage enabled item with the default git option::

    >>> backends.value
    ['git']
    >>> browser.getControl('Save').click()
    >>> browser.url
    'http://nohost/plone/storage_enabled/view'

Inspect the underlying object to see that the marker interfaces and the
annotation is set correctly::

    >>> from zope.annotation.interfaces import IAnnotations
    >>> IAnnotations(portal.storage_enabled)[
    ...     'repodono.storage.base.StorageFactory']
    {'backend': 'git'}

The path associated with the instance should be stored in the path
attribute within the IStorageInfo instance and it should exist::

    >>> from os.path import exists, join
    >>> from repodono.storage.interfaces import IStorageInfo
    >>> exists(IStorageInfo(portal.storage_enabled).path)
    True
    >>> exists(join(IStorageInfo(portal.storage_enabled).path, '.git'))
    True

Naturally, the IStorage adapter should acquire the associated GitStorage
instance::

    >>> from repodono.storage.interfaces import IStorage
    >>> IStorage(portal.storage_enabled)
    <repodono.backend.git.utility.GitStorage object at ...>

Rendering
---------

The rendering is ultimately done by repodono.storage, done using the
mockup-structure-pattern with vocabulary provided by the JSON endpoint
``getStorageVocabulary``.  First we should populate it with some data::

    >>> from repodono.backend.git.testing import util
    >>> testdir = join(IStorageInfo(portal.storage_enabled).path, '.git')
    >>> revs, fulllist = util.create_demo_git_repo(testdir)

Then::

    >>> import json
    >>> browser.open(
    ...     'http://nohost/plone/storage_enabled/getStorageVocabulary')
    >>> result = json.loads(browser.contents)
    >>> result['total']
    4
    >>> result['results'][0]['id'] == 'nested'
    True
