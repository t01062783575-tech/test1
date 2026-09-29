import os
import threading
import time

import pytest

from epiccut.engine import runner
from epiccut.errors import RenderCancelled, RenderError
from epiccut.utils.tempdirs import scoped_temp_dir
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_cancellation_stops_the_subprocess_and_cleans_up(tmp_path):
    output_path = str(tmp_path / "cancelled.mp4")
    # A deliberately slow encode (high resolution, slow preset, several
    # seconds of source) so there is a real window to cancel mid-render.
    argv = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30:duration=20",
        "-c:v", "libx264", "-preset", "veryslow", "-pix_fmt", "yuv420p",
        output_path,
    ]

    cancel_event = threading.Event()

    def _cancel_soon():
        time.sleep(0.5)
        cancel_event.set()

    threading.Thread(target=_cancel_soon, daemon=True).start()

    with pytest.raises(RenderCancelled):
        runner.run_ffmpeg(argv, output_path, cancel_event=cancel_event, poll_interval=0.02)

    assert not os.path.exists(output_path)
    assert not os.path.exists(output_path + ".epiccut-inprogress.json")


@requires_ffmpeg
def test_failed_render_cleans_up_partial_output_and_marker(tmp_path):
    output_path = str(tmp_path / "failed.mp4")
    argv = ["ffmpeg", "-y", "-i", "/nonexistent/does-not-exist.mp4", output_path]

    with pytest.raises(RenderError):
        runner.run_ffmpeg(argv, output_path)

    assert not os.path.exists(output_path)
    assert not os.path.exists(output_path + ".epiccut-inprogress.json")


@requires_ffmpeg
def test_successful_render_removes_marker_but_keeps_output(tmp_path):
    output_path = str(tmp_path / "ok.mp4")
    argv = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=320x240:rate=24:duration=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = runner.run_ffmpeg(argv, output_path)

    assert result.returncode == 0
    assert os.path.exists(output_path)
    assert not os.path.exists(output_path + ".epiccut-inprogress.json")


def test_scoped_temp_dir_cleans_up_on_success():
    captured_path = None
    with scoped_temp_dir() as path:
        captured_path = path
        assert os.path.isdir(path)
        with open(os.path.join(path, "frame_0001.png"), "wb") as f:
            f.write(b"fake frame data")
    assert not os.path.exists(captured_path)


def test_scoped_temp_dir_cleans_up_on_exception():
    captured_path = None
    with pytest.raises(ValueError):
        with scoped_temp_dir() as path:
            captured_path = path
            assert os.path.isdir(path)
            raise ValueError("boom")
    assert not os.path.exists(captured_path)


def test_find_and_cleanup_incomplete_renders(tmp_path):
    output_path = str(tmp_path / "interrupted.mp4")
    # Simulate a container being killed mid-render: partial output + marker
    # exist, but no ffmpeg process is actually running anymore.
    with open(output_path, "wb") as f:
        f.write(b"partial garbage bytes")
    with open(output_path + ".epiccut-inprogress.json", "w") as f:
        f.write('{"output": "%s", "started_at": 0}' % output_path)

    found = runner.find_incomplete_renders(str(tmp_path))
    assert output_path in found

    runner.cleanup_incomplete_render(output_path)

    assert not os.path.exists(output_path)
    assert not os.path.exists(output_path + ".epiccut-inprogress.json")
    assert runner.find_incomplete_renders(str(tmp_path)) == []
