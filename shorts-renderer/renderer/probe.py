"""ffprobe wrapper and post-render verification against the spec."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from fractions import Fraction

from renderer.errors import VerificationError

DURATION_TOLERANCE_SECONDS = 0.1
_ENCODER_TO_CODEC_NAME = {"libx264": "h264", "libx265": "hevc"}


@dataclass
class MediaInfo:
    duration: float
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str | None
    has_audio: bool
    audio_codec: str | None
    audio_sample_rate: int | None
    audio_duration: float | None
    bit_rate: int | None


def _frame_rate(rate_str: str | None) -> float | None:
    if not rate_str or rate_str in ("0/0", "N/A"):
        return None
    try:
        return float(Fraction(rate_str))
    except (ValueError, ZeroDivisionError):
        return None


def probe(path: str) -> MediaInfo:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise VerificationError("ffprobe was not found on PATH")

    proc = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise VerificationError(f"ffprobe failed on '{path}': {proc.stderr.strip()}")

    data = json.loads(proc.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration") or (v or a or {}).get("duration") or 0.0)
    bit_rate = int(fmt["bit_rate"]) if fmt.get("bit_rate") else None

    return MediaInfo(
        duration=duration,
        width=int(v["width"]) if v and "width" in v else None,
        height=int(v["height"]) if v and "height" in v else None,
        fps=_frame_rate(v.get("avg_frame_rate") or v.get("r_frame_rate")) if v else None,
        video_codec=v.get("codec_name") if v else None,
        has_audio=a is not None,
        audio_codec=a.get("codec_name") if a else None,
        audio_sample_rate=int(a["sample_rate"]) if a and a.get("sample_rate") else None,
        audio_duration=float(a["duration"]) if a and a.get("duration") else None,
        bit_rate=bit_rate,
    )


def expected_codec_name(encoder: str) -> str:
    return _ENCODER_TO_CODEC_NAME.get(encoder, encoder)


def verify(path: str, *, expected_duration: float, expected_width: int, expected_height: int,
           expected_fps: float, expected_video_codec: str, expect_audio: bool,
           expected_audio_rate: int | None = None) -> tuple[bool, list[str], MediaInfo]:
    import os

    issues: list[str] = []
    if not os.path.exists(path):
        return False, [f"output does not exist: {path}"], None  # type: ignore[return-value]
    if os.path.getsize(path) == 0:
        issues.append("output file is empty (0 bytes)")

    info = probe(path)

    if abs(info.duration - expected_duration) > DURATION_TOLERANCE_SECONDS:
        issues.append(f"duration {info.duration:.3f}s != expected {expected_duration:.3f}s (tolerance {DURATION_TOLERANCE_SECONDS}s)")
    if info.width != expected_width or info.height != expected_height:
        issues.append(f"dimensions {info.width}x{info.height} != expected {expected_width}x{expected_height}")
    if info.fps is not None and abs(info.fps - expected_fps) > 0.5:
        issues.append(f"fps {info.fps} != expected {expected_fps}")
    if info.video_codec != expected_video_codec:
        issues.append(f"video codec '{info.video_codec}' != expected '{expected_video_codec}'")
    if expect_audio and not info.has_audio:
        issues.append("expected an audio stream but none was found")
    if not expect_audio and info.has_audio:
        issues.append("output has an audio stream but none was expected")
    if expect_audio and expected_audio_rate and info.audio_sample_rate != expected_audio_rate:
        issues.append(f"audio sample rate {info.audio_sample_rate} != expected {expected_audio_rate}")
    if not info.bit_rate or info.bit_rate <= 0:
        issues.append("output has zero or unknown bitrate")
    if info.duration <= 0:
        issues.append("output has zero duration (likely a zero-frame export)")
    if expect_audio and info.has_audio and info.audio_duration is not None:
        if abs(info.audio_duration - info.duration) > DURATION_TOLERANCE_SECONDS * 2:
            issues.append(f"audio duration {info.audio_duration:.3f}s and video duration {info.duration:.3f}s are out of sync")

    return len(issues) == 0, issues, info
