# -*- coding: utf-8 -*-
try:
    from repodono.backend.git.testing.layers import (
        RepodonoBackendGitLayer,
        REPODONO_BACKEND_GIT_FIXTURE,
        REPODONO_BACKEND_GIT_INTEGRATION_TESTING,
        REPODONO_BACKEND_GIT_FUNCTIONAL_TESTING,
        REPODONO_BACKEND_GIT_ACCEPTANCE_TESTING,
    )

    __all__ = [
        'RepodonoBackendGitLayer',
        'REPODONO_BACKEND_GIT_FIXTURE',
        'REPODONO_BACKEND_GIT_INTEGRATION_TESTING',
        'REPODONO_BACKEND_GIT_FUNCTIONAL_TESTING',
        'REPODONO_BACKEND_GIT_ACCEPTANCE_TESTING',
    ]
except ImportError:
    pass
