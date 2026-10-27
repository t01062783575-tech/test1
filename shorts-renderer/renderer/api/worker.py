"""Async job execution: a bounded thread pool runs the *existing*
`renderer.runner.run_job` — nothing about rendering itself is reimplemented
here, only the "accept a job now, run it in the background, remember the
result" wiring the HTTP layer needs.
"""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from renderer.api.jobstore import JobStore
from renderer.logging_setup import get_logger
from renderer.runner import run_job
from renderer.schema import VideoSpec

logger = get_logger()


class JobManager:
    def __init__(self, store: JobStore, output_dir: str, *, concurrency: int = 2,
                 render_timeout: float = 600.0, max_render_timeout: float = 900.0):
        self.store = store
        self.output_dir = output_dir
        self.render_timeout = render_timeout
        self.max_render_timeout = max_render_timeout
        os.makedirs(output_dir, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="render-worker")
        # Guards the "does this job_id already exist?" check + the queued-row
        # insert as one atomic unit, so two near-simultaneous POSTs with the
        # same job_id can never both pass the check and both get submitted —
        # this is the "never render duplicates automatically" guarantee.
        self._submit_lock = threading.Lock()

    def submit(self, spec: VideoSpec, *, requested_timeout: float | None = None):
        """Returns (job_record, created: bool). created=False means this
        job_id already existed and nothing new was submitted — the caller
        (server.py) reports the existing job's current state instead."""
        with self._submit_lock:
            existing = self.store.get(spec.job_id)
            if existing is not None:
                logger.info("duplicate submit ignored", extra={"job_id": spec.job_id, "event": "idempotent_hit"})
                return existing, False

            record = self.store.create_queued(spec.job_id, json.dumps(spec_to_dict(spec), ensure_ascii=False))

        timeout = min(requested_timeout, self.max_render_timeout) if requested_timeout else self.render_timeout
        self._executor.submit(self._run, spec, timeout)
        return record, True

    def _run(self, spec: VideoSpec, timeout: float) -> None:
        self.store.mark_processing(spec.job_id)
        output_path = os.path.join(self.output_dir, f"{spec.job_id}.mp4")
        result = run_job(spec, output_path, timeout=timeout)
        if result.status == "completed":
            self.store.mark_completed(
                spec.job_id, output_path=result.output_path,
                width=result.width, height=result.height, duration=result.duration,
            )
        else:
            self.store.mark_failed(spec.job_id, error=result.error or "render failed for an unknown reason")

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)


def spec_to_dict(spec: VideoSpec) -> dict:
    """Minimal, loggable/storable summary of a spec — intentionally not a
    full re-serialization (schema.py owns the real recipe shape); this is
    just enough to audit what a job_id was requested with."""
    return {
        "job_id": spec.job_id,
        "output": {"width": spec.output.width, "height": spec.output.height, "fps": spec.output.fps},
        "scene_count": len(spec.scenes),
        "has_voiceover": spec.voiceover is not None,
        "has_music": spec.background_music is not None,
    }
