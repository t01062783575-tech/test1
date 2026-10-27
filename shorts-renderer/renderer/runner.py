"""Run a render job end to end: build the ffmpeg command, execute it with a
timeout, verify the output with ffprobe, and always clean up temp files —
success, failure, or timeout alike.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass

from renderer.errors import RendererError, RenderFailedError, RenderTimeoutError, VerificationError
from renderer.ffmpeg_build import build_render_command
from renderer.logging_setup import get_logger
from renderer.probe import expected_codec_name, verify
from renderer.schema import VideoSpec

logger = get_logger()


@dataclass
class JobResult:
    job_id: str
    status: str  # "completed" | "failed"
    output_path: str | None
    width: int
    height: int
    duration: float
    error: str | None = None


def run_job(spec: VideoSpec, output_path: str, *, timeout: float = 600.0, verify_output: bool = True) -> JobResult:
    job_id = spec.job_id
    logger.info("job started", extra={"job_id": job_id, "event": "job_start"})

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    work_dir = tempfile.mkdtemp(prefix=f"shorts-render-{job_id}-")
    start = time.monotonic()
    try:
        built = build_render_command(spec, work_dir, output_path)
        logger.info("command built", extra={"job_id": job_id, "event": "command_built"})

        try:
            proc = subprocess.run(
                built.argv,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            _remove_partial(output_path)
            logger.error("render timed out", extra={"job_id": job_id, "event": "timeout"})
            raise RenderTimeoutError(f"render exceeded {timeout}s timeout") from exc

        elapsed = time.monotonic() - start

        if proc.returncode != 0:
            _remove_partial(output_path)
            tail = "\n".join(proc.stderr.strip().splitlines()[-30:])
            logger.error("render failed", extra={"job_id": job_id, "event": "render_failed", "returncode": proc.returncode})
            raise RenderFailedError(f"ffmpeg exited with code {proc.returncode}:\n{tail}")

        logger.info("render finished", extra={"job_id": job_id, "event": "render_finished", "duration_s": round(elapsed, 2)})

        if verify_output:
            ok, issues, info = verify(
                output_path,
                expected_duration=built.expected_duration,
                expected_width=spec.output.width,
                expected_height=spec.output.height,
                expected_fps=spec.output.fps,
                expected_video_codec=expected_codec_name(spec.output.video_codec),
                expect_audio=built.expects_audio,
                expected_audio_rate=spec.output.audio_rate if built.expects_audio else None,
            )
            if not ok:
                logger.error("verification failed", extra={"job_id": job_id, "event": "verification_failed"})
                raise VerificationError("output failed verification: " + "; ".join(issues))
            logger.info("verification passed", extra={"job_id": job_id, "event": "verification_passed"})

        return JobResult(
            job_id=job_id,
            status="completed",
            output_path=output_path,
            width=spec.output.width,
            height=spec.output.height,
            duration=built.expected_duration,
        )

    except RendererError as exc:
        # Covers build-time failures too (e.g. a missing/unreachable asset
        # raises AssetError from build_render_command, before any ffmpeg
        # subprocess ever starts) — every expected failure mode becomes a
        # reported "failed" job, never an uncaught exception.
        logger.error("job failed", extra={"job_id": job_id, "event": "job_failed"})
        return JobResult(
            job_id=job_id, status="failed", output_path=None,
            width=spec.output.width, height=spec.output.height, duration=0.0, error=str(exc),
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _remove_partial(output_path: str) -> None:
    try:
        os.remove(output_path)
    except FileNotFoundError:
        pass
