"""The input JSON video specification: structure and validation.

This is intentionally a plain-dict-in, dataclass-out design (no pydantic/
jsonschema dependency) so the service has zero paid or third-party runtime
dependencies beyond the Python standard library and ffmpeg itself — "low
cost" per the brief. Every field a Make.com scenario would need to supply
(background per scene, animated text, subtitles, voice-over, music, fades/
transitions, safe zones) is covered; nothing here depends on any specific
Make scenario, so the same spec can be produced by Make, a test, or a human
hand-writing JSON.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from renderer.errors import SpecError

SUPPORTED_FITS = {"cover", "contain"}
SUPPORTED_BACKGROUND_KINDS = {"image", "video"}
SUPPORTED_TRANSITIONS = {"none", "fade", "dissolve"}
SUPPORTED_TEXT_POSITIONS = {"top", "center", "bottom", "custom"}
SUPPORTED_TEXT_ANIMATIONS = {"none", "fade", "slide_up"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


@dataclass
class OutputSpec:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    video_codec: str = "libx264"
    pix_fmt: str = "yuv420p"
    audio_codec: str = "aac"
    audio_rate: int = 48000
    crf: int = 20

    @classmethod
    def from_dict(cls, d: dict | None) -> "OutputSpec":
        d = d or {}
        known = {k: d[k] for k in d if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class AudioInput:
    source: str
    volume: float = 1.0
    start: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0

    @classmethod
    def from_dict(cls, d: dict | None) -> "AudioInput | None":
        if not d:
            return None
        _require("source" in d, "audio input requires 'source'")
        return cls(
            source=d["source"],
            volume=float(d.get("volume", 1.0)),
            start=float(d.get("start", 0.0)),
            fade_in=float(d.get("fade_in", 0.0)),
            fade_out=float(d.get("fade_out", 0.0)),
        )


@dataclass
class Background:
    source: str
    kind: str = "image"
    fit: str = "cover"

    @classmethod
    def from_dict(cls, d: dict) -> "Background":
        _require("source" in d, "scene background requires 'source'")
        kind = d.get("kind", "image")
        fit = d.get("fit", "cover")
        _require(kind in SUPPORTED_BACKGROUND_KINDS, f"unknown background kind '{kind}'")
        _require(fit in SUPPORTED_FITS, f"unknown background fit '{fit}'")
        return cls(source=d["source"], kind=kind, fit=fit)


@dataclass
class Transition:
    type: str = "none"
    duration: float = 0.4

    @classmethod
    def from_dict(cls, d: dict | None) -> "Transition":
        d = d or {}
        t = d.get("type", "none")
        _require(t in SUPPORTED_TRANSITIONS, f"unknown transition type '{t}'")
        return cls(type=t, duration=float(d.get("duration", 0.4)))


@dataclass
class TextOverlay:
    content: str
    position: str = "bottom"
    y: int | None = None
    font_size: int = 64
    color: str = "white"
    bold: bool = True
    start: float = 0.0
    end: float | None = None
    animation: str = "none"

    @classmethod
    def from_dict(cls, d: dict) -> "TextOverlay":
        _require("content" in d and isinstance(d["content"], str), "text overlay requires string 'content'")
        position = d.get("position", "bottom")
        animation = d.get("animation", "none")
        _require(position in SUPPORTED_TEXT_POSITIONS, f"unknown text position '{position}'")
        _require(animation in SUPPORTED_TEXT_ANIMATIONS, f"unknown text animation '{animation}'")
        if position == "custom":
            _require(d.get("y") is not None, "text position 'custom' requires 'y'")
        return cls(
            content=d["content"],
            position=position,
            y=d.get("y"),
            font_size=int(d.get("font_size", 64)),
            color=d.get("color", "white"),
            bold=bool(d.get("bold", True)),
            start=float(d.get("start", 0.0)),
            end=d.get("end"),
            animation=animation,
        )


@dataclass
class Subtitle:
    text: str
    start: float
    end: float

    @classmethod
    def from_dict(cls, d: dict) -> "Subtitle":
        for k in ("text", "start", "end"):
            _require(k in d, f"subtitle requires '{k}'")
        _require(float(d["end"]) > float(d["start"]), "subtitle 'end' must be after 'start'")
        return cls(text=d["text"], start=float(d["start"]), end=float(d["end"]))


@dataclass
class Scene:
    id: str
    duration: float
    background: Background
    transition_in: Transition = field(default_factory=Transition)
    texts: list[TextOverlay] = field(default_factory=list)
    subtitles: list[Subtitle] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict, index: int) -> "Scene":
        _require("background" in d, f"scene #{index} requires 'background'")
        _require("duration" in d, f"scene #{index} requires 'duration'")
        duration = float(d["duration"])
        _require(duration > 0, f"scene #{index} duration must be positive (got {duration})")
        return cls(
            id=d.get("id", f"scene_{index}"),
            duration=duration,
            background=Background.from_dict(d["background"]),
            transition_in=Transition.from_dict(d.get("transition_in")),
            texts=[TextOverlay.from_dict(t) for t in d.get("texts", [])],
            subtitles=[Subtitle.from_dict(s) for s in d.get("subtitles", [])],
        )


@dataclass
class SafeZones:
    top: int = 0
    bottom: int = 0

    @classmethod
    def from_dict(cls, d: dict | None) -> "SafeZones":
        d = d or {}
        return cls(top=int(d.get("top", 0)), bottom=int(d.get("bottom", 0)))


@dataclass
class VideoSpec:
    job_id: str
    output: OutputSpec = field(default_factory=OutputSpec)
    safe_zones: SafeZones = field(default_factory=SafeZones)
    voiceover: AudioInput | None = None
    background_music: AudioInput | None = None
    scenes: list[Scene] = field(default_factory=list)
    fade_in: float = 0.0
    fade_out: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VideoSpec":
        _require(isinstance(d, dict), "spec must be a JSON object")
        _require("scenes" in d and isinstance(d["scenes"], list) and len(d["scenes"]) > 0,
                  "spec requires a non-empty 'scenes' array")

        scenes = [Scene.from_dict(s, i) for i, s in enumerate(d["scenes"])]
        output = OutputSpec.from_dict(d.get("output"))
        _require(output.width > 0 and output.height > 0, "output width/height must be positive")
        _require(output.fps in (24, 25, 30, 60), f"unsupported fps {output.fps} (use 24, 25, 30, or 60)")

        return cls(
            job_id=d.get("job_id") or str(uuid.uuid4()),
            output=output,
            safe_zones=SafeZones.from_dict(d.get("safe_zones")),
            voiceover=AudioInput.from_dict(d.get("voiceover")),
            background_music=AudioInput.from_dict(d.get("background_music")),
            scenes=scenes,
            fade_in=float(d.get("fade_in", 0.0)),
            fade_out=float(d.get("fade_out", 0.0)),
        )

    def total_duration(self) -> float:
        """Sum of scene durations minus the overlap consumed by crossfade
        transitions (an N-second 'fade' transition_in on scene k shortens
        the timeline by N seconds, same as EpicCut's xfade chain)."""
        total = sum(s.duration for s in self.scenes)
        for scene in self.scenes[1:]:
            if scene.transition_in.type != "none":
                total -= scene.transition_in.duration
        return total
