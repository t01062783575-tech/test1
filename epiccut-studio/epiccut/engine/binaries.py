"""Locate required external binaries.

FFmpeg is the render engine (per spec). We check for it explicitly and raise
a clear, typed error rather than letting a bare `FileNotFoundError` from
`subprocess` surface as a stack trace to a non-technical user.
"""

from __future__ import annotations

import functools
import shutil

from epiccut.errors import BinaryNotFoundError


@functools.lru_cache(maxsize=None)
def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise BinaryNotFoundError(
            "ffmpeg was not found on PATH. EpicCut Studio requires ffmpeg as its render "
            "engine — install it (e.g. 'apt install ffmpeg', 'brew install ffmpeg', or "
            "download a build from ffmpeg.org) and make sure it is on PATH."
        )
    return path


@functools.lru_cache(maxsize=None)
def find_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if path is None:
        raise BinaryNotFoundError(
            "ffprobe was not found on PATH. It ships alongside ffmpeg in almost every "
            "distribution — reinstalling ffmpeg usually fixes this."
        )
    return path


def ffmpeg_available() -> bool:
    try:
        find_ffmpeg()
        return True
    except BinaryNotFoundError:
        return False


def ffprobe_available() -> bool:
    try:
        find_ffprobe()
        return True
    except BinaryNotFoundError:
        return False
