"""Locate a font file that can render both Korean and English text.

Noto Sans CJK KR covers Hangul, Latin, and most punctuation in one file —
one font for both languages in the spec (`Korean and English font support`)
instead of per-language font-switching logic. Falls back through a short
list of other common CJK-capable fonts before giving up with a clear error
naming what to install.
"""

from __future__ import annotations

import functools
import shutil
import subprocess

from renderer.errors import AssetError

_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def _fc_match(pattern: str) -> str | None:
    if shutil.which("fc-match") is None:
        return None
    try:
        proc = subprocess.run(["fc-match", "--format=%{file}", pattern], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return None


@functools.lru_cache(maxsize=None)
def find_korean_capable_font() -> str:
    import os

    for path in _CANDIDATES:
        if os.path.isfile(path):
            return path

    for pattern in ("Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "Malgun Gothic", "AppleSDGothicNeo"):
        found = _fc_match(pattern)
        if found and os.path.isfile(found):
            return found

    raise AssetError(
        "No Korean-capable font was found (checked Noto Sans CJK KR and common fallbacks). "
        "Install one, e.g. 'apt install fonts-noto-cjk' on Debian/Ubuntu, and try again."
    )
