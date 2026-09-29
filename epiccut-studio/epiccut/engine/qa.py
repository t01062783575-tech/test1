"""Post-export quality assurance: verify a rendered file actually matches
what the recipe asked for, using ffprobe as the source of truth. Called
automatically after every export, from the CLI, the GUI, and tests alike.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from epiccut.engine.probe import probe_media
from epiccut.errors import ProbeError, QAError

DURATION_TOLERANCE_SECONDS = 0.1

# ffprobe reports the codec (e.g. "h264"), not the ffmpeg *encoder* used to
# produce it (e.g. "libx264", "h264_nvenc", "h264_videotoolbox"). QA needs
# to compare like with like regardless of which encoder rendered the file.
_ENCODER_TO_CODEC_NAME = {
    "libx264": "h264", "h264_nvenc": "h264", "h264_videotoolbox": "h264", "h264_qsv": "h264", "h264_vaapi": "h264",
    "libx265": "hevc", "hevc_nvenc": "hevc", "hevc_videotoolbox": "hevc", "hevc_qsv": "hevc",
}


def expected_codec_name(encoder: str) -> str:
    """Map an ffmpeg encoder name (as used in `-c:v`) to the codec name
    ffprobe reports (`codec_name`)."""
    return _ENCODER_TO_CODEC_NAME.get(encoder, encoder)


@dataclass
class QAExpectation:
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str | None = None
    expect_audio: bool = False


@dataclass
class QAReport:
    ok: bool
    issues: list[str]
    duration: float
    width: int | None
    height: int | None
    fps: float | None
    has_audio: bool
    bit_rate: int | None


def verify_export(output_path: str, expectation: QAExpectation) -> QAReport:
    issues: list[str] = []

    if not os.path.exists(output_path):
        return QAReport(ok=False, issues=[f"output file does not exist: {output_path}"],
                         duration=0.0, width=None, height=None, fps=None, has_audio=False, bit_rate=None)

    if os.path.getsize(output_path) == 0:
        issues.append("output file is empty (0 bytes)")

    try:
        info = probe_media(output_path)
    except ProbeError as exc:
        issues.append(f"ffprobe could not read the output: {exc}")
        return QAReport(ok=False, issues=issues, duration=0.0, width=None, height=None,
                         fps=None, has_audio=False, bit_rate=None)

    if abs(info.duration - expectation.duration) > DURATION_TOLERANCE_SECONDS:
        issues.append(
            f"duration {info.duration:.3f}s differs from expected {expectation.duration:.3f}s "
            f"by more than {DURATION_TOLERANCE_SECONDS}s"
        )

    if info.width != expectation.width or info.height != expectation.height:
        issues.append(
            f"dimensions {info.width}x{info.height} != expected {expectation.width}x{expectation.height}"
        )

    if info.fps is not None and abs(info.fps - expectation.fps) > 0.5:
        issues.append(f"frame rate {info.fps:.3f} != expected {expectation.fps:.3f}")

    if expectation.video_codec is not None and info.video_codec != expectation.video_codec:
        issues.append(f"video codec '{info.video_codec}' != expected '{expectation.video_codec}'")

    if expectation.expect_audio and not info.has_audio:
        issues.append("expected an audio stream but none was found")
    if not expectation.expect_audio and info.has_audio:
        issues.append("output has an audio stream but none was expected")

    if not info.bit_rate or info.bit_rate <= 0:
        issues.append("output has zero or unknown bitrate")

    if info.duration <= 0:
        issues.append("output has zero (or unreadable) duration — likely a zero-frame export")

    if expectation.expect_audio and info.has_audio and info.audio_duration is not None:
        if abs(info.audio_duration - info.duration) > DURATION_TOLERANCE_SECONDS * 2:
            issues.append(
                f"audio stream duration {info.audio_duration:.3f}s and video duration "
                f"{info.duration:.3f}s are out of sync"
            )

    return QAReport(
        ok=len(issues) == 0,
        issues=issues,
        duration=info.duration,
        width=info.width,
        height=info.height,
        fps=info.fps,
        has_audio=info.has_audio,
        bit_rate=info.bit_rate,
    )


def verify_export_or_raise(output_path: str, expectation: QAExpectation) -> QAReport:
    report = verify_export(output_path, expectation)
    if not report.ok:
        raise QAError("export QA failed: " + "; ".join(report.issues))
    return report
