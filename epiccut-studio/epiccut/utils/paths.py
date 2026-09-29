"""Path helpers.

The one rule that matters here: **never build a shell command string**.
`subprocess.run`/`Popen` with a list argv passes each element to the OS
exactly as-is — spaces, Korean characters, or any other Unicode in a path
need no quoting or escaping at all. This module exists mainly to make that
rule explicit and give it a single, tested home rather than relying on every
call site to remember it.
"""

from __future__ import annotations

import os


def ensure_parent_dir(path: str) -> None:
    """Create the parent directory of `path` if it doesn't exist yet."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def as_argv_safe(path: str) -> str:
    """Identity function, deliberately.

    Exists so call sites read as an explicit statement of intent ("this
    path is going straight into an argv list, not a shell string") and so a
    future change in how we invoke ffmpeg has one place to update. Never
    shell-quote the result of this function — argv lists don't need it, and
    quoting them would corrupt paths that already need no escaping.
    """
    return path
