"""ffprobe wrapper: inspect a media file and return structured MediaInfo.

This is step 1 of the Epic Surreal Auto Finish pipeline ("inspect source
with ffprobe") and is also used standalone by the retiming calculator and
the CLI's `surreal` command.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from fractions import Fraction

from epiccut.engine.binaries import find_ffprobe
from epiccut.errors import ProbeError


@dataclass
class MediaInfo:
    path: str
    duration: float
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str | None
    has_audio: bool
    audio_codec: str | None
    audio_duration: float | None
    bit_rate: int | None
    rotation: int = 0  # degrees, from stream side-data/tags, 0 if not rotated


def _parse_frame_rate(rate_str: str | None) -> float | None:
    if not rate_str or rate_str in ("0/0", "N/A"):
        return None
    try:
        return float(Fraction(rate_str))
    except (ValueError, ZeroDivisionError):
        return None


def probe_media(path: str) -> MediaInfo:
    """Run ffprobe on `path` and return a MediaInfo. Raises ProbeError on
    any failure (missing file, corrupt media, ffprobe crash, unparsable
    output) so callers get one exception type to handle."""

    ffprobe = find_ffprobe()
    cmd = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as exc:
        raise ProbeError(f"ffprobe timed out inspecting '{path}'") from exc
    except OSError as exc:
        raise ProbeError(f"failed to run ffprobe on '{path}': {exc}") from exc

    if proc.returncode != 0:
        raise ProbeError(f"ffprobe failed on '{path}': {proc.stderr.strip()}")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"ffprobe returned unparsable output for '{path}'") from exc

    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video_stream is None and audio_stream is None:
        raise ProbeError(f"'{path}' has no video or audio streams ffprobe could read")

    try:
        duration = float(fmt.get("duration") or (video_stream or audio_stream or {}).get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        raise ProbeError(f"ffprobe could not determine a usable duration for '{path}'")

    rotation = 0
    if video_stream is not None:
        tags = video_stream.get("tags", {}) or {}
        try:
            rotation = int(tags.get("rotate", 0))
        except (TypeError, ValueError):
            rotation = 0
        for side_data in video_stream.get("side_data_list", []) or []:
            if "rotation" in side_data:
                try:
                    rotation = int(side_data["rotation"])
                except (TypeError, ValueError):
                    pass

    bit_rate = None
    if fmt.get("bit_rate") is not None:
        try:
            bit_rate = int(fmt["bit_rate"])
        except ValueError:
            bit_rate = None

    return MediaInfo(
        path=path,
        duration=duration,
        width=int(video_stream["width"]) if video_stream and "width" in video_stream else None,
        height=int(video_stream["height"]) if video_stream and "height" in video_stream else None,
        fps=_parse_frame_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")) if video_stream else None,
        video_codec=video_stream.get("codec_name") if video_stream else None,
        has_audio=audio_stream is not None,
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        audio_duration=float(audio_stream["duration"]) if audio_stream and audio_stream.get("duration") else None,
        bit_rate=bit_rate,
        rotation=rotation,
    )
