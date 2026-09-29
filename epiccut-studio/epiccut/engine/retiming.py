"""Retiming math: turn a source duration + target duration into a single,
continuous speed factor — never a loop or a concatenation.

This module is pure arithmetic (no subprocess calls) so it can be unit
tested exhaustively without ffmpeg, and so the GUI (Phase C) can preview the
computed factor live while the user drags a target-duration slider.
"""

from __future__ import annotations

from dataclasses import dataclass

# Beyond this speed-change ratio (either direction) plain FFmpeg retiming
# ("setpts") risks visible judder on slow, mostly-static AI-generated
# footage. This is a *recommendation* threshold for optional RIFE frame
# interpolation — retiming still proceeds without it; nothing is blocked.
DEFAULT_JUDDER_THRESHOLD = 1.6


@dataclass
class RetimingPlan:
    source_duration: float
    target_duration: float
    speed_factor: float  # ffmpeg setpts multiplier: >1 slows down, <1 speeds up
    playback_rate: float  # 1 / speed_factor — how fast the clip now plays back
    judder_risk: bool
    recommend_rife: bool


def compute_retiming(
    source_duration: float,
    target_duration: float,
    *,
    judder_threshold: float = DEFAULT_JUDDER_THRESHOLD,
    allow_interpolation: bool = False,
) -> RetimingPlan:
    """Compute the constant speed factor that stretches/compresses a clip of
    `source_duration` seconds into exactly `target_duration` seconds via a
    single continuous timestretch (ffmpeg `setpts=<factor>*PTS`).

    Example (the canonical case from the spec): a 5.04s clip retimed to a
    12s target needs `speed_factor = 12 / 5.04 ≈ 2.381` — the clip plays
    back at `1 / 2.381 ≈ 0.42x` speed, filling exactly 12 continuous
    seconds with no repeated or concatenated frames.
    """

    if source_duration <= 0:
        raise ValueError(f"source_duration must be positive, got {source_duration}")
    if target_duration <= 0:
        raise ValueError(f"target_duration must be positive, got {target_duration}")

    speed_factor = target_duration / source_duration
    playback_rate = 1.0 / speed_factor

    change_ratio = max(speed_factor, 1.0 / speed_factor)
    judder_risk = change_ratio >= judder_threshold

    return RetimingPlan(
        source_duration=source_duration,
        target_duration=target_duration,
        speed_factor=speed_factor,
        playback_rate=playback_rate,
        judder_risk=judder_risk,
        recommend_rife=judder_risk and not allow_interpolation,
    )


def setpts_filter(speed_factor: float) -> str:
    """The ffmpeg video filter expression for a constant-speed retime."""
    if speed_factor <= 0:
        raise ValueError(f"speed_factor must be positive, got {speed_factor}")
    return f"setpts={speed_factor:.10f}*PTS"


def output_fps_for_retiming(source_fps: float, speed_factor: float, target_fps: float | None = None) -> float:
    """Frame rate to request on the output after a `setpts` retime.

    Slowing a clip down (speed_factor > 1) stretches existing frames over a
    longer span; without an explicit target fps we keep the *source* fps so
    motion sampling density doesn't change (this is also why extreme
    slow-downs are judder-risk candidates for RIFE, which actually
    synthesizes new frames rather than just re-timing existing ones).
    """
    if target_fps is not None:
        return target_fps
    return source_fps
