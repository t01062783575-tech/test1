import shutil
import subprocess

import pytest

FFMPEG_PRESENT = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
requires_ffmpeg = pytest.mark.skipif(not FFMPEG_PRESENT, reason="ffmpeg/ffprobe not available")


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"fixture generation failed: {' '.join(cmd)}\n{proc.stderr}")


def make_test_image(path: str, width: int, height: int, color: str = "blue") -> str:
    ffmpeg = shutil.which("ffmpeg")
    _run([ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}", "-frames:v", "1", path])
    return path


def make_test_video(path: str, duration: float, width: int, height: int, fps: int = 30) -> str:
    ffmpeg = shutil.which("ffmpeg")
    _run([
        ffmpeg, "-y", "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate={fps}:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", path,
    ])
    return path


def make_test_audio(path: str, duration: float, frequency: int = 440) -> str:
    ffmpeg = shutil.which("ffmpeg")
    _run([ffmpeg, "-y", "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={duration}", "-c:a", "aac", path])
    return path


@pytest.fixture
def two_scene_spec_paths(tmp_path):
    """Local asset files for a minimal 2-scene spec."""
    bg1 = make_test_image(str(tmp_path / "bg1.png"), 1920, 1080, color="navy")
    bg2 = make_test_image(str(tmp_path / "bg2.png"), 1920, 1080, color="darkred")
    voice = make_test_audio(str(tmp_path / "voice.aac"), duration=7.0, frequency=300)
    music = make_test_audio(str(tmp_path / "music.aac"), duration=30.0, frequency=600)
    return {"bg1": bg1, "bg2": bg2, "voice": voice, "music": music}
