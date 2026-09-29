"""RIFE (Real-Time Intermediate Flow Estimation) frame interpolation adapter.

Phase A ships real, working *detection* — `is_available()` genuinely checks
whether a usable RIFE executable is configured — and a stub `interpolate()`
that raises `NotImplementedError` if ever called. The real interpolation
body is Phase D. `retiming.compute_retiming(..., allow_interpolation=...)`
and the Auto Finish pipeline (Phase B) only ever call `interpolate()` after
checking `is_available()`, so an unconfigured RIFE never crashes a render —
it just means the recommendation to use it is silently not actable yet.
"""

from __future__ import annotations

import os
import shutil


class RifeAdapter:
    def __init__(self, executable: str | None = None):
        # Highest priority: explicit path. Then an env var the user can set
        # once. Then a bare `rife-ncnn-vulkan` on PATH, the most common
        # distributed build name.
        self._executable = executable or os.environ.get("EPICCUT_RIFE_PATH")

    def _resolved_executable(self) -> str | None:
        if self._executable:
            return self._executable if os.path.isfile(self._executable) else None
        return shutil.which("rife-ncnn-vulkan")

    def is_available(self) -> bool:
        return self._resolved_executable() is not None

    def unavailable_reason(self) -> str | None:
        if self.is_available():
            return None
        return (
            "RIFE was not found. Set EPICCUT_RIFE_PATH to a rife-ncnn-vulkan build, or "
            "install one on PATH, to enable optional frame interpolation. Rendering will "
            "continue with FFmpeg-only retiming."
        )

    def interpolate(
        self,
        input_frames_dir: str,
        output_frames_dir: str,
        *,
        target_fps: int,
        strength: float = 0.5,
        on_progress=None,
    ) -> None:
        if not self.is_available():
            raise RuntimeError(self.unavailable_reason())
        raise NotImplementedError(
            "RIFE interpolation body ships in Phase D; detection/fallback (Phase A) is complete."
        )
