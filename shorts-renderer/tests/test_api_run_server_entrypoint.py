"""Exercise `renderer.api.server.run_server` itself — the integration tests
in test_api_server_integration.py construct the ThreadingHTTPServer
directly and never call `run_server`, which once hid a crash-on-startup bug
(a reserved `logging` kwarg collision) that no other test caught."""

import threading
import time
import urllib.request

from renderer.api.server import run_server


def test_run_server_starts_and_serves_healthz(tmp_path, monkeypatch):
    monkeypatch.setenv("SHORTS_RENDERER_API_KEY", "run-server-test-key")
    port = 8199

    thread = threading.Thread(
        target=run_server,
        kwargs=dict(
            host="127.0.0.1", port=port,
            db_path=str(tmp_path / "jobs.sqlite3"),
            output_dir=str(tmp_path / "render_output"),
            concurrency=1,
        ),
        daemon=True,
    )
    thread.start()
    try:
        deadline = time.time() + 5
        last_exc = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1) as resp:
                    assert resp.status == 200
                    return
            except Exception as exc:  # noqa: BLE001 - server may not have bound the port yet
                last_exc = exc
                time.sleep(0.2)
        raise AssertionError(f"server never became reachable: {last_exc}")
    finally:
        pass  # daemon thread; process teardown (pytest exit) reclaims the socket
