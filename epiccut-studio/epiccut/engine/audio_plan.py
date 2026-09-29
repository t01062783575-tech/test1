"""Music trim/offset/fade/volume planning — pure logic, no subprocess calls.

Turns an `AudioSettings` selection (e.g. "full track, start 60.0s, duration
12s, fade in 0.5s, fade out 1.0s, volume 0.30") into concrete ffmpeg filter
expressions and the `-ss`/`-t` input-trim arguments, independent of how the
result is actually invoked (used by both `command_builder.py` and tests).
"""

from __future__ import annotations

from dataclasses import dataclass

from epiccut.schema.recipe import AudioSettings


@dataclass
class AudioPlan:
    start: float
    duration: float | None
    filters: list[str]
    volume: float

    def filter_chain(self) -> str:
        return ",".join(self.filters) if self.filters else "anull"


def plan_music(audio: AudioSettings, source_duration: float | None = None) -> AudioPlan:
    """Build an AudioPlan from an AudioSettings selection.

    `source_duration` (if known, from ffprobe) is used only to validate that
    `start` doesn't run past the end of the source; it is not required.
    """

    if audio.start < 0:
        raise ValueError(f"audio start must be >= 0, got {audio.start}")
    if audio.duration is not None and audio.duration <= 0:
        raise ValueError(f"audio duration must be positive if set, got {audio.duration}")
    if audio.fade_in < 0 or audio.fade_out < 0:
        raise ValueError("audio fade_in/fade_out must be >= 0")
    if source_duration is not None and audio.start >= source_duration:
        raise ValueError(
            f"audio start ({audio.start}s) is at or past the source duration ({source_duration}s)"
        )

    filters: list[str] = []

    if audio.volume != 1.0:
        filters.append(f"volume={audio.volume:.6f}")

    if audio.fade_in > 0:
        filters.append(f"afade=t=in:st=0:d={audio.fade_in:.6f}")

    if audio.fade_out > 0:
        if audio.duration is not None:
            fade_out_start = max(0.0, audio.duration - audio.fade_out)
            filters.append(f"afade=t=out:st={fade_out_start:.6f}:d={audio.fade_out:.6f}")
        else:
            # Duration not fixed (e.g. full remaining track): fade relative
            # to output end isn't expressible without a known duration, so
            # the command builder applies this via `-af ... apad`-free
            # trailing fade computed once the real output duration is known.
            filters.append(f"afade=t=out:d={audio.fade_out:.6f}")

    if audio.normalize:
        # loudnorm single-pass (fast, good-enough default; a two-pass mode
        # is a Phase B refinement once we measure real-world targets).
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    if audio.limiter:
        filters.append("alimiter=limit=0.95")

    return AudioPlan(start=audio.start, duration=audio.duration, filters=filters, volume=audio.volume)
