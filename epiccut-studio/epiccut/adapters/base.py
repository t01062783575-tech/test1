"""Shared shape for optional third-party AI adapters (RIFE, Real-ESRGAN,
Whisper, ...).

The rule the whole engine depends on: **an adapter being unavailable must
never crash the base editor.** Every call site checks `is_available()`
first and falls back to a pure-FFmpeg path when it's `False`. Nothing in
`epiccut.engine` imports a third-party AI package directly at module load
time — only these adapter modules do, and only inside functions, so a
missing dependency raises `ImportError` at the moment of use (caught by
`is_available()`), not at `import epiccut`.
"""

from __future__ import annotations

from typing import Protocol


class OptionalAdapter(Protocol):
    def is_available(self) -> bool: ...

    def unavailable_reason(self) -> str | None: ...
