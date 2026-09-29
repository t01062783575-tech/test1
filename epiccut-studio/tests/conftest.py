import shutil
import subprocess

import pytest

from epiccut.engine.binaries import ffmpeg_available, ffprobe_available

FFMPEG_PRESENT = ffmpeg_available() and ffprobe_available()

requires_ffmpeg = pytest.mark.skipif(not FFMPEG_PRESENT, reason="ffmpeg/ffprobe not available in this environment")


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"fixture generation failed: {' '.join(cmd)}\n{proc.stderr}")


def make_test_video(path: str, duration: float, width: int = 640, height: int = 360, fps: int = 24) -> str:
    """Generate a tiny synthetic video (color bars pattern) with ffmpeg's
    `testsrc` lavfi source — no external footage needed for tests."""
    ffmpeg = shutil.which("ffmpeg")
    _run([
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate={fps}:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        path,
    ])
    return path


def make_test_audio(path: str, duration: float, frequency: int = 440) -> str:
    """Generate a tiny synthetic tone as a music-track stand-in."""
    ffmpeg = shutil.which("ffmpeg")
    codec = "libmp3lame" if path.endswith(".mp3") else "aac"
    _run([
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={duration}",
        "-c:a", codec,
        path,
    ])
    return path


@pytest.fixture
def landscape_video_5_04s(tmp_path):
    """The canonical spec case: a 5.04s landscape (16:9) AI-style clip."""
    path = tmp_path / "kling_source.mp4"
    return make_test_video(str(path), duration=5.04, width=960, height=540, fps=24)


@pytest.fixture
def music_track_90s(tmp_path):
    path = tmp_path / "ambient.mp3"
    return make_test_audio(str(path), duration=90.0)
