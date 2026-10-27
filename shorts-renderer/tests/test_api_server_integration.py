"""Real HTTP requests against a real running server — this is the suite
that actually proves "Make.com can request a true 1080x1920 MP4 from our
FFmpeg renderer" over HTTP, not just via the Python API.
"""

import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from renderer.api.jobstore import JobStore
from renderer.api.server import make_handler
from renderer.api.worker import JobManager
from renderer.probe import probe
from tests.conftest import requires_ffmpeg

API_KEY = "integration-test-key"


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    monkeypatch.setenv("SHORTS_RENDERER_API_KEY", API_KEY)
    store = JobStore(str(tmp_path / "jobs.sqlite3"))
    manager = JobManager(store, str(tmp_path / "render_output"), concurrency=2)
    handler_cls = make_handler(manager, base_url="http://127.0.0.1:0")  # overwritten per-test below

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = httpd.server_address[1]
    # Rebuild with the real port now known, so signed URLs are self-consistent.
    handler_cls = make_handler(manager, base_url=f"http://127.0.0.1:{port}")
    httpd.RequestHandlerClass = handler_cls

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    httpd.shutdown()
    manager.shutdown()
    store.close()


def _request(method, url, *, headers=None, body=None, timeout=10):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8")) if resp.headers.get("Content-Type") == "application/json" else resp.read()
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            return exc.code, json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            return exc.code, payload


def test_healthz_requires_no_auth(running_server):
    status, body = _request("GET", f"{running_server}/healthz")
    assert status == 200
    assert body == {"status": "ok"}


def test_render_without_auth_is_rejected(running_server, two_scene_spec_paths):
    status, body = _request("POST", f"{running_server}/render", body=_spec(two_scene_spec_paths))
    assert status == 401


def test_render_with_wrong_token_is_rejected(running_server, two_scene_spec_paths):
    status, body = _request(
        "POST", f"{running_server}/render",
        headers={"Authorization": "Bearer wrong-key", "Content-Type": "application/json"},
        body=_spec(two_scene_spec_paths),
    )
    assert status == 401


def test_job_lookup_requires_auth(running_server):
    status, body = _request("GET", f"{running_server}/jobs/some-job")
    assert status == 401


def test_unknown_job_id_404(running_server):
    status, body = _request("GET", f"{running_server}/jobs/does-not-exist", headers=_auth())
    assert status == 404


def test_invalid_spec_rejected_with_400(running_server):
    status, body = _request("POST", f"{running_server}/render", headers=_auth(), body={"scenes": []})
    assert status == 400
    assert "error" in body


@requires_ffmpeg
def test_api_initiated_render_full_lifecycle(running_server, two_scene_spec_paths):
    """The completion-criteria render: POST /render -> poll GET /jobs/{id}
    through queued/processing -> completed -> download via signed URL ->
    verify the bytes with ffprobe independently."""
    spec = _spec(two_scene_spec_paths, job_id="api-lifecycle-test")

    status, body = _request("POST", f"{running_server}/render", headers=_auth(), body=spec)
    assert status == 202
    assert body["job_id"] == "api-lifecycle-test"
    assert body["status"] == "queued"
    assert body["created"] is True

    final = _poll_until_terminal(running_server, "api-lifecycle-test")
    assert final["status"] == "completed", final
    assert final["width"] == 1080
    assert final["height"] == 1920

    status, signed = _request("GET", f"{running_server}/jobs/api-lifecycle-test/signed-url", headers=_auth())
    assert status == 200
    assert "url" in signed and "exp=" in signed["url"] and "sig=" in signed["url"]

    # Download via the signed URL, WITHOUT any Authorization header — this is
    # exactly what Make's http:DownloadFile (authenticationType: noAuth)
    # does against the existing Render_URL today.
    out_path = _download(signed["url"])
    info = probe(out_path)
    assert info.width == 1080
    assert info.height == 1920
    assert info.video_codec == "h264"
    assert info.has_audio is True
    assert info.audio_codec == "aac"
    assert info.audio_sample_rate == 48000


@requires_ffmpeg
def test_duplicate_job_id_is_idempotent_not_a_second_render(running_server, two_scene_spec_paths):
    spec = _spec(two_scene_spec_paths, job_id="idempotent-test")

    status1, body1 = _request("POST", f"{running_server}/render", headers=_auth(), body=spec)
    status2, body2 = _request("POST", f"{running_server}/render", headers=_auth(), body=spec)

    assert status1 == 202
    assert body1["created"] is True
    assert status2 == 200  # not 202 — nothing new was queued
    assert body2["created"] is False
    assert body2["job_id"] == body1["job_id"]

    _poll_until_terminal(running_server, "idempotent-test")


def test_output_requires_auth_or_valid_signature(running_server):
    status, body = _request("GET", f"{running_server}/jobs/some-job/output")
    assert status == 401


def test_output_rejects_expired_or_bad_signature(running_server):
    status, body = _request("GET", f"{running_server}/jobs/some-job/output?exp=1&sig=deadbeef")
    assert status == 401


def test_output_not_ready_returns_409(running_server, two_scene_spec_paths):
    spec = _spec(two_scene_spec_paths, job_id="not-ready-test")
    _request("POST", f"{running_server}/render", headers=_auth(), body=spec)
    # Immediately (before the background render can finish) ask for output.
    status, body = _request("GET", f"{running_server}/jobs/not-ready-test/output", headers=_auth())
    assert status in (409,)  # queued or processing, never "ready" this fast


def _auth():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _spec(paths, job_id=None):
    d = {
        "output": {"width": 1080, "height": 1920, "fps": 30},
        "voiceover": {"source": paths["voice"]},
        "background_music": {"source": paths["music"], "volume": 0.15},
        "scenes": [
            {"duration": 2.0, "background": {"source": paths["bg1"]}, "texts": [{"content": "API 렌더 테스트"}]},
            {"duration": 2.0, "background": {"source": paths["bg2"]}, "transition_in": {"type": "fade", "duration": 0.3}},
        ],
    }
    if job_id:
        d["job_id"] = job_id
    return d


def _poll_until_terminal(base_url, job_id, timeout=60):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        status, body = _request("GET", f"{base_url}/jobs/{job_id}", headers=_auth())
        last = body
        if body.get("status") in ("completed", "failed"):
            return body
        time.sleep(0.5)
    raise TimeoutError(f"job did not finish within {timeout}s, last state: {last}")


def _download(url):
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".mp4")
    import os
    os.close(fd)
    urllib.request.urlretrieve(url, path)
    return path
