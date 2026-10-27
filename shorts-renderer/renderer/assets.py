"""Resolve a spec's asset references (local paths or http(s) URLs, matching
how Make.com scenarios actually hand off assets in this pipeline — e.g. the
existing `Render_URL`/`Asset_Screenshot_URL` fields are Backblaze/Cloudinary
URLs) into local file paths ffmpeg can read.

No paid service is used here: plain `urllib` over HTTP(S), nothing more.
"""

from __future__ import annotations

import os
import urllib.request
import uuid
from urllib.parse import urlparse

from renderer.errors import AssetError

_MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024  # 200MB safety cap for a single asset


def is_url(source: str) -> bool:
    return urlparse(source).scheme in ("http", "https")


def resolve_asset(source: str, work_dir: str, *, timeout: float = 30.0) -> str:
    """Return a local filesystem path for `source`. Local paths are
    returned as-is (after existence check); http(s) URLs are downloaded
    into `work_dir` under a random filename that preserves the extension."""

    if not is_url(source):
        if not os.path.isfile(source):
            raise AssetError(f"asset not found: '{source}'")
        return source

    parsed = urlparse(source)
    _, ext = os.path.splitext(parsed.path)
    local_name = f"{uuid.uuid4().hex}{ext}"
    local_path = os.path.join(work_dir, local_name)

    try:
        with urllib.request.urlopen(source, timeout=timeout) as resp:
            total = 0
            with open(local_path, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > _MAX_DOWNLOAD_BYTES:
                        raise AssetError(f"asset '{source}' exceeded the {_MAX_DOWNLOAD_BYTES} byte download cap")
                    f.write(chunk)
    except AssetError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any network/HTTP failure as a clean AssetError
        raise AssetError(f"failed to download asset '{source}': {exc}") from exc

    if os.path.getsize(local_path) == 0:
        raise AssetError(f"downloaded asset '{source}' is empty")

    return local_path
