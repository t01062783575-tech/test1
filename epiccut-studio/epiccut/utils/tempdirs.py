"""Guaranteed temp-directory cleanup.

Every temp directory anywhere in the engine (RIFE frame extraction, Real-
ESRGAN tiling, etc. in later phases) should be created through this one
context manager so cleanup happens in a `finally` block exactly once,
instead of each call site reimplementing (and potentially forgetting) it.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager


@contextmanager
def scoped_temp_dir(prefix: str = "epiccut-"):
    """Yield a fresh temp directory path; remove it (recursively, ignoring
    errors for already-gone files) when the block exits, even on
    exception."""
    path = tempfile.mkdtemp(prefix=prefix)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
