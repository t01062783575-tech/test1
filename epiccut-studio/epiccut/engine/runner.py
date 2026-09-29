"""Run a built ffmpeg command as a subprocess: progress reporting,
cooperative cancellation, and crash-safe cleanup.

Interrupted-render recovery (Phase A scope): before starting, we write a
small JSON marker file next to the output recording that a render is in
progress; it is removed on success. `find_incomplete_renders` can scan a
directory for leftover markers after an interruption (container restart,
process kill) so a future run can at least *detect* and report the
incomplete state. Actually resuming a partially-encoded ffmpeg output
mid-stream is out of scope for Phase A — see FEATURE_MATRIX.md — so an
interrupted render today is detected and cleaned up, then simply restarted
by the caller.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable

from epiccut.errors import RenderCancelled, RenderError

ProgressCallback = Callable[[dict], None]

_MARKER_SUFFIX = ".epiccut-inprogress.json"


def _marker_path(output_path: str) -> str:
    return output_path + _MARKER_SUFFIX


def _write_marker(output_path: str) -> None:
    with open(_marker_path(output_path), "w", encoding="utf-8") as f:
        json.dump({"output": output_path, "started_at": time.time()}, f)


def _remove_marker(output_path: str) -> None:
    try:
        os.remove(_marker_path(output_path))
    except FileNotFoundError:
        pass


def find_incomplete_renders(directory: str) -> list[str]:
    """Return output paths whose render was interrupted (marker file exists
    but no matching successful-completion marker removal happened)."""
    incomplete = []
    for name in os.listdir(directory):
        if name.endswith(_MARKER_SUFFIX):
            incomplete.append(os.path.join(directory, name[: -len(_MARKER_SUFFIX)]))
    return incomplete


def cleanup_incomplete_render(output_path: str) -> None:
    """Remove a partial output file and its marker, so a fresh render can
    start clean."""
    try:
        os.remove(output_path)
    except FileNotFoundError:
        pass
    _remove_marker(output_path)


def _parse_progress_line(line: str, state: dict) -> dict | None:
    key, _, value = line.strip().partition("=")
    if not key:
        return None
    state[key] = value
    if key == "progress":  # ffmpeg emits this as the last field of each block
        return dict(state)
    return None


@dataclass
class RunResult:
    output_path: str
    returncode: int
    cancelled: bool


def run_ffmpeg(
    argv: list[str],
    output_path: str,
    *,
    cancel_event: threading.Event | None = None,
    on_progress: ProgressCallback | None = None,
    poll_interval: float = 0.1,
) -> RunResult:
    """Execute an ffmpeg argv list, reporting progress and honoring
    cooperative cancellation.

    On cancellation: terminates the subprocess, removes the partial output
    file and the in-progress marker, and raises `RenderCancelled`.
    On failure: removes the partial output file and marker, and raises
    `RenderError` with ffmpeg's stderr tail.
    On success: removes the marker and returns a `RunResult`.
    """

    argv_with_progress = list(argv)
    # Insert `-progress pipe:1` right after the binary so it applies
    # globally; ffmpeg accepts global options anywhere before the first
    # output, but placing it right after argv[0] is simplest and safe.
    argv_with_progress[1:1] = ["-progress", "pipe:1", "-nostats"]

    _write_marker(output_path)

    proc = subprocess.Popen(
        argv_with_progress,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stderr_lines: list[str] = []
    progress_state: dict = {}

    def _drain_stderr():
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_lines.append(line)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    cancelled = False
    try:
        assert proc.stdout is not None
        while True:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break

            line = proc.stdout.readline()
            if line == "" and proc.poll() is not None:
                break
            if not line:
                time.sleep(poll_interval)
                continue

            block = _parse_progress_line(line, progress_state)
            if block is not None and on_progress is not None:
                on_progress(block)

        stderr_thread.join(timeout=5)

        if cancelled:
            cleanup_incomplete_render(output_path)
            raise RenderCancelled("render was cancelled")

        returncode = proc.wait()
        if returncode != 0:
            cleanup_incomplete_render(output_path)
            tail = "".join(stderr_lines[-40:])
            raise RenderError(f"ffmpeg exited with code {returncode}:\n{tail}")

        _remove_marker(output_path)
        return RunResult(output_path=output_path, returncode=returncode, cancelled=False)

    except BaseException:
        if proc.poll() is None:
            proc.kill()
        raise
