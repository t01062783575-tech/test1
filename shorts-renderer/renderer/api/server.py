"""Minimal authenticated HTTP rendering API.

    POST /render                      (Bearer auth)  -> 202 {job_id, status}
    GET  /jobs/{job_id}                (Bearer auth)  -> job status + metadata
    GET  /jobs/{job_id}/signed-url     (Bearer auth)  -> {url, expires_at}
    GET  /jobs/{job_id}/output         (Bearer auth OR valid signed-url query params) -> the MP4 bytes
    GET  /healthz                      (no auth)       -> liveness only, no job data

Built on the standard library's `http.server` — consistent with the rest of
this project's zero-third-party-runtime-dependency design (see
requirements.txt) and entirely adequate at the request volume described in
PHASE3_DESIGN.md. Every route that touches job data or triggers a render
requires authentication; there is no public unauthenticated render path.
"""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from renderer.api.auth import (
    DEFAULT_SIGNED_URL_TTL_SECONDS,
    check_bearer_token,
    sign_job_output,
    verify_signed_output_url,
)
from renderer.api.jobstore import STATUS_COMPLETED, JobStore
from renderer.api.worker import JobManager
from renderer.errors import RendererError
from renderer.logging_setup import get_logger
from renderer.schema import VideoSpec

logger = get_logger()

MAX_BODY_BYTES = 2 * 1024 * 1024  # a video spec is a small JSON document; 2MB is generous
MAX_RENDER_TIMEOUT = 900.0

_JOB_PATH = re.compile(r"^/jobs/([A-Za-z0-9_.\-]+)$")
_JOB_OUTPUT_PATH = re.compile(r"^/jobs/([A-Za-z0-9_.\-]+)/output$")
_JOB_SIGNED_URL_PATH = re.compile(r"^/jobs/([A-Za-z0-9_.\-]+)/signed-url$")


def make_handler(job_manager: JobManager, base_url: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "shorts-renderer/0.1"

        def log_message(self, fmt: str, *args) -> None:  # noqa: A003 - BaseHTTPRequestHandler API
            # Route stdlib's default stderr logging through our structured
            # logger instead. `args` here is only (request-line, status,
            # size) — never headers — so no Authorization value can leak.
            # (Note: "message" is a reserved LogRecord attribute name, so
            # the detail goes under "detail", not "message".)
            logger.info("http request", extra={"event": "http_request", "detail": fmt % args})

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            return check_bearer_token(self.headers.get("Authorization"))

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path == "/healthz":
                self._send_json(200, {"status": "ok"})
                return

            m = _JOB_OUTPUT_PATH.match(path)
            if m:
                self._handle_get_output(m.group(1), query)
                return

            m = _JOB_SIGNED_URL_PATH.match(path)
            if m:
                self._handle_get_signed_url(m.group(1))
                return

            m = _JOB_PATH.match(path)
            if m:
                self._handle_get_job(m.group(1))
                return

            self._send_json(404, {"error": "not found"})

        def _handle_get_job(self, job_id: str) -> None:
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            record = job_manager.store.get(job_id)
            if record is None:
                self._send_json(404, {"error": f"no job '{job_id}'"})
                return
            self._send_json(200, record.to_public_dict())

        def _handle_get_signed_url(self, job_id: str) -> None:
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            record = job_manager.store.get(job_id)
            if record is None:
                self._send_json(404, {"error": f"no job '{job_id}'"})
                return
            if record.status != STATUS_COMPLETED:
                self._send_json(409, {"error": f"job is '{record.status}', not completed yet"})
                return
            signature, expires_at = sign_job_output(job_id, DEFAULT_SIGNED_URL_TTL_SECONDS)
            url = f"{base_url}/jobs/{job_id}/output?exp={expires_at}&sig={signature}"
            self._send_json(200, {"url": url, "expires_at": expires_at})

        def _handle_get_output(self, job_id: str, query: dict) -> None:
            authorized = self._authorized()
            if not authorized:
                exp = query.get("exp", [None])[0]
                sig = query.get("sig", [None])[0]
                authorized = verify_signed_output_url(job_id, exp, sig)
            if not authorized:
                self._send_json(401, {"error": "unauthorized"})
                return

            record = job_manager.store.get(job_id)
            if record is None:
                self._send_json(404, {"error": f"no job '{job_id}'"})
                return
            if record.status != STATUS_COMPLETED or not record.output_path:
                self._send_json(409, {"error": f"job is '{record.status}', output not available"})
                return
            if not os.path.exists(record.output_path):
                self._send_json(410, {"error": "output file no longer available"})
                return

            size = os.path.getsize(record.output_path)
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", f'attachment; filename="{job_id}.mp4"')
            self.end_headers()
            with open(record.output_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    self.wfile.write(chunk)

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if urlparse(self.path).path != "/render":
                self._send_json(404, {"error": "not found"})
                return
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return

            length = self.headers.get("Content-Length")
            if length is None or not length.isdigit():
                self._send_json(411, {"error": "Content-Length required"})
                return
            if int(length) > MAX_BODY_BYTES:
                self._send_json(413, {"error": f"request body exceeds {MAX_BODY_BYTES} bytes"})
                return

            raw = self.rfile.read(int(length))
            try:
                body = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": f"invalid JSON body: {exc}"})
                return

            requested_timeout = body.pop("timeout", None) if isinstance(body, dict) else None

            try:
                spec = VideoSpec.from_dict(body)
            except RendererError as exc:
                self._send_json(400, {"error": f"invalid spec: {exc}"})
                return

            record, created = job_manager.submit(spec, requested_timeout=requested_timeout)
            status_code = 202 if created else 200
            self._send_json(status_code, {
                "job_id": record.job_id,
                "status": record.status,
                "created": created,
            })

    return Handler


def run_server(*, host: str = "127.0.0.1", port: int = 8080, db_path: str = "jobs.sqlite3",
               output_dir: str = "render_output", concurrency: int = 2, base_url: str | None = None) -> None:
    from renderer.api.auth import ensure_configured

    ensure_configured()  # raises AuthNotConfigured if SHORTS_RENDERER_API_KEY is unset

    store = JobStore(db_path)
    manager = JobManager(store, output_dir, concurrency=concurrency)
    effective_base_url = base_url or f"http://{host}:{port}"
    handler_cls = make_handler(manager, effective_base_url)

    httpd = ThreadingHTTPServer((host, port), handler_cls)
    logger.info("server starting", extra={"event": "server_start", "detail": f"{host}:{port}"})
    try:
        httpd.serve_forever()
    finally:
        manager.shutdown()
        store.close()
