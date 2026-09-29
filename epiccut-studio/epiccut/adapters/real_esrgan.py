"""Real-ESRGAN upscaling adapter — same detect-now/implement-in-Phase-D
pattern as `rife.py`. When unavailable, `upscale.py`-consuming code (Phase B)
falls back to a high-quality FFmpeg lanczos scale, per spec.
"""

from __future__ import annotations

import os
import shutil


class RealEsrganAdapter:
    def __init__(self, executable: str | None = None):
        self._executable = executable or os.environ.get("EPICCUT_REALESRGAN_PATH")

    def _resolved_executable(self) -> str | None:
        if self._executable:
            return self._executable if os.path.isfile(self._executable) else None
        return shutil.which("realesrgan-ncnn-vulkan")

    def is_available(self) -> bool:
        return self._resolved_executable() is not None

    def unavailable_reason(self) -> str | None:
        if self.is_available():
            return None
        return (
            "Real-ESRGAN was not found. Set EPICCUT_REALESRGAN_PATH to a realesrgan-ncnn-vulkan "
            "build, or install one on PATH, to enable AI upscaling. Rendering will fall back to "
            "a high-quality FFmpeg lanczos scale."
        )

    def upscale(self, input_path: str, output_path: str, *, factor: float, on_progress=None) -> None:
        if not self.is_available():
            raise RuntimeError(self.unavailable_reason())
        raise NotImplementedError(
            "Real-ESRGAN upscaling body ships in Phase D; detection/fallback (Phase A) is complete."
        )
