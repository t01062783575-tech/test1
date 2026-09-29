"""The EpicCut Studio recipe: the single serializable source of truth.

Every field the GUI (Phase C) will eventually expose already has a home here,
per the project mandate that "every UI operation must be representable as a
JSON editing recipe" and "the same project must be executable through desktop
GUI / CLI / a future HTTP API". Phase A's engine only *renders* a subset of
this (constant-speed clips, basic transform/crop/fade, project audio) — the
rest (keyframe evaluation, non-constant speed curves, visual effects) is
schema-complete now and engine-complete in later phases, exactly as tracked in
FEATURE_MATRIX.md.

Every dataclass below implements `to_dict` / `from_dict` explicitly (rather
than relying on generic (de)serialization) so validation errors are precise
and so the format is stable independent of Python's dataclass internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from epiccut.errors import RecipeError

RECIPE_SCHEMA_VERSION = "0.1.0"

_INTERPOLATIONS = {"linear", "ease_in", "ease_out", "ease_in_out"}
_MEDIA_KINDS = {"video", "audio", "image"}
_TRACK_KINDS = {"video", "audio", "overlay"}
_SPEED_MODES = {"constant", "custom", "target_duration"}
_TRANSITION_KINDS = {"cut", "crossfade", "dissolve", "fade_to_black", "custom"}
_REFRAME_ASPECTS = {"9:16", "1:1", "4:5", "16:9"}
_REFRAME_MODES = {"center_crop", "manual_focal"}
_UPSCALE_MODES = {"none", "1.5x", "2x", "4x"}
_UPSCALE_ENGINES = {"auto", "real_esrgan", "ffmpeg"}
_STABILIZATION_PRESETS = {"minimal", "balanced", "strong"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RecipeError(message)


@dataclass
class Keyframe:
    time: float
    value: Any  # float, or [x, y] for position keyframes
    interpolation: str = "linear"

    def to_dict(self) -> dict:
        return {"time": self.time, "value": self.value, "interpolation": self.interpolation}

    @classmethod
    def from_dict(cls, d: dict) -> "Keyframe":
        _require("time" in d and "value" in d, "keyframe requires 'time' and 'value'")
        interp = d.get("interpolation", "linear")
        _require(interp in _INTERPOLATIONS, f"unknown interpolation '{interp}'")
        return cls(time=float(d["time"]), value=d["value"], interpolation=interp)


@dataclass
class KeyframedProperty:
    """A property that is either a single static value or an animated one.

    `static_value` is used when `keyframes` is empty; once keyframes exist
    the static value is ignored (kept only as a convenient default/preview).
    """

    static_value: Any = None
    keyframes: list[Keyframe] = field(default_factory=list)

    def is_keyframed(self) -> bool:
        return len(self.keyframes) > 0

    def to_dict(self) -> dict:
        return {
            "static_value": self.static_value,
            "keyframes": [k.to_dict() for k in self.keyframes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KeyframedProperty":
        return cls(
            static_value=d.get("static_value"),
            keyframes=[Keyframe.from_dict(k) for k in d.get("keyframes", [])],
        )

    @classmethod
    def constant(cls, value: Any) -> "KeyframedProperty":
        return cls(static_value=value, keyframes=[])


@dataclass
class Transform:
    position: KeyframedProperty = field(default_factory=lambda: KeyframedProperty.constant([0.0, 0.0]))
    scale: KeyframedProperty = field(default_factory=lambda: KeyframedProperty.constant(1.0))
    rotation: KeyframedProperty = field(default_factory=lambda: KeyframedProperty.constant(0.0))
    opacity: KeyframedProperty = field(default_factory=lambda: KeyframedProperty.constant(1.0))

    def to_dict(self) -> dict:
        return {
            "position": self.position.to_dict(),
            "scale": self.scale.to_dict(),
            "rotation": self.rotation.to_dict(),
            "opacity": self.opacity.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "Transform":
        if not d:
            return cls()
        return cls(
            position=KeyframedProperty.from_dict(d["position"]) if "position" in d else KeyframedProperty.constant([0.0, 0.0]),
            scale=KeyframedProperty.from_dict(d["scale"]) if "scale" in d else KeyframedProperty.constant(1.0),
            rotation=KeyframedProperty.from_dict(d["rotation"]) if "rotation" in d else KeyframedProperty.constant(0.0),
            opacity=KeyframedProperty.from_dict(d["opacity"]) if "opacity" in d else KeyframedProperty.constant(1.0),
        )


@dataclass
class Crop:
    x: float = 0.0
    y: float = 0.0
    width: float | None = None
    height: float | None = None

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, d: dict | None) -> "Crop | None":
        if d is None:
            return None
        return cls(x=d.get("x", 0.0), y=d.get("y", 0.0), width=d.get("width"), height=d.get("height"))


@dataclass
class SpeedCurve:
    """Retiming spec for a clip.

    mode="constant": `factor` is applied directly (setpts style; >1 slows
        down, <1 speeds up).
    mode="target_duration": the engine computes `factor` from the clip's
        probed source duration and this target (the 5.04s -> 12s case).
    mode="custom": `points` is a list of (time, factor) pairs describing a
        speed curve; schema-complete in Phase A, evaluated starting Phase B.
    """

    mode: str = "constant"
    factor: float = 1.0
    target_duration: float | None = None
    points: list[list[float]] = field(default_factory=list)
    allow_interpolation: bool = False

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "factor": self.factor,
            "target_duration": self.target_duration,
            "points": self.points,
            "allow_interpolation": self.allow_interpolation,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "SpeedCurve":
        if not d:
            return cls()
        mode = d.get("mode", "constant")
        _require(mode in _SPEED_MODES, f"unknown speed mode '{mode}'")
        return cls(
            mode=mode,
            factor=float(d.get("factor", 1.0)),
            target_duration=d.get("target_duration"),
            points=[list(p) for p in d.get("points", [])],
            allow_interpolation=bool(d.get("allow_interpolation", False)),
        )


@dataclass
class FadeSettings:
    fade_in: float = 0.0
    fade_out: float = 0.0

    def to_dict(self) -> dict:
        return {"fade_in": self.fade_in, "fade_out": self.fade_out}

    @classmethod
    def from_dict(cls, d: dict | None) -> "FadeSettings":
        if not d:
            return cls()
        return cls(fade_in=float(d.get("fade_in", 0.0)), fade_out=float(d.get("fade_out", 0.0)))


@dataclass
class MediaRef:
    id: str
    path: str
    kind: str  # video | audio | image

    def to_dict(self) -> dict:
        return {"id": self.id, "path": self.path, "kind": self.kind}

    @classmethod
    def from_dict(cls, d: dict) -> "MediaRef":
        _require("id" in d and "path" in d and "kind" in d, "media entry requires id/path/kind")
        _require(d["kind"] in _MEDIA_KINDS, f"unknown media kind '{d['kind']}'")
        return cls(id=d["id"], path=d["path"], kind=d["kind"])


@dataclass
class Clip:
    id: str
    media_id: str
    track_id: str
    source_in: float = 0.0
    source_out: float | None = None  # None = to end of source
    timeline_start: float = 0.0
    transform: Transform = field(default_factory=Transform)
    crop: Crop | None = None
    speed: SpeedCurve = field(default_factory=SpeedCurve)
    fade: FadeSettings = field(default_factory=FadeSettings)
    freeze_frame_at: float | None = None
    freeze_frame_duration: float = 0.0
    reverse: bool = False
    volume: KeyframedProperty = field(default_factory=lambda: KeyframedProperty.constant(1.0))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "media_id": self.media_id,
            "track_id": self.track_id,
            "source_in": self.source_in,
            "source_out": self.source_out,
            "timeline_start": self.timeline_start,
            "transform": self.transform.to_dict(),
            "crop": self.crop.to_dict() if self.crop else None,
            "speed": self.speed.to_dict(),
            "fade": self.fade.to_dict(),
            "freeze_frame_at": self.freeze_frame_at,
            "freeze_frame_duration": self.freeze_frame_duration,
            "reverse": self.reverse,
            "volume": self.volume.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Clip":
        for k in ("id", "media_id", "track_id"):
            _require(k in d, f"clip requires '{k}'")
        return cls(
            id=d["id"],
            media_id=d["media_id"],
            track_id=d["track_id"],
            source_in=float(d.get("source_in", 0.0)),
            source_out=d.get("source_out"),
            timeline_start=float(d.get("timeline_start", 0.0)),
            transform=Transform.from_dict(d.get("transform")),
            crop=Crop.from_dict(d.get("crop")),
            speed=SpeedCurve.from_dict(d.get("speed")),
            fade=FadeSettings.from_dict(d.get("fade")),
            freeze_frame_at=d.get("freeze_frame_at"),
            freeze_frame_duration=float(d.get("freeze_frame_duration", 0.0)),
            reverse=bool(d.get("reverse", False)),
            volume=KeyframedProperty.from_dict(d["volume"]) if "volume" in d else KeyframedProperty.constant(1.0),
        )


@dataclass
class Transition:
    clip_a_id: str
    clip_b_id: str
    kind: str = "crossfade"
    duration: float = 0.5

    def to_dict(self) -> dict:
        return {
            "clip_a_id": self.clip_a_id,
            "clip_b_id": self.clip_b_id,
            "kind": self.kind,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transition":
        for k in ("clip_a_id", "clip_b_id"):
            _require(k in d, f"transition requires '{k}'")
        kind = d.get("kind", "crossfade")
        _require(kind in _TRANSITION_KINDS, f"unknown transition kind '{kind}'")
        return cls(clip_a_id=d["clip_a_id"], clip_b_id=d["clip_b_id"], kind=kind, duration=float(d.get("duration", 0.5)))


@dataclass
class Track:
    id: str
    kind: str  # video | audio | overlay
    clips: list[Clip] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "clips": [c.to_dict() for c in self.clips],
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Track":
        _require("id" in d and "kind" in d, "track requires 'id' and 'kind'")
        _require(d["kind"] in _TRACK_KINDS, f"unknown track kind '{d['kind']}'")
        return cls(
            id=d["id"],
            kind=d["kind"],
            clips=[Clip.from_dict(c) for c in d.get("clips", [])],
            enabled=bool(d.get("enabled", True)),
        )


@dataclass
class AudioSettings:
    """Project-level music settings — the "music source / start / duration /
    fade in / fade out / volume" selection described in the spec."""

    source_media_id: str | None = None
    start: float = 0.0
    duration: float | None = None
    fade_in: float = 0.0
    fade_out: float = 0.0
    volume: float = 1.0
    normalize: bool = False
    limiter: bool = False
    mute: bool = False
    eq: dict | None = None
    compressor: dict | None = None
    ducking: dict | None = None

    def to_dict(self) -> dict:
        return {
            "source_media_id": self.source_media_id,
            "start": self.start,
            "duration": self.duration,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "volume": self.volume,
            "normalize": self.normalize,
            "limiter": self.limiter,
            "mute": self.mute,
            "eq": self.eq,
            "compressor": self.compressor,
            "ducking": self.ducking,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "AudioSettings | None":
        if d is None:
            return None
        return cls(
            source_media_id=d.get("source_media_id"),
            start=float(d.get("start", 0.0)),
            duration=d.get("duration"),
            fade_in=float(d.get("fade_in", 0.0)),
            fade_out=float(d.get("fade_out", 0.0)),
            volume=float(d.get("volume", 1.0)),
            normalize=bool(d.get("normalize", False)),
            limiter=bool(d.get("limiter", False)),
            mute=bool(d.get("mute", False)),
            eq=d.get("eq"),
            compressor=d.get("compressor"),
            ducking=d.get("ducking"),
        )


@dataclass
class EnhancementSettings:
    exposure: float = 0.0
    contrast: float = 0.0
    highlights: float = 0.0
    shadows: float = 0.0
    saturation: float = 0.0
    temperature: float = 0.0
    tint: float = 0.0
    gamma: float = 1.0
    sharpen: float = 0.0
    denoise: float = 0.0
    vignette: float = 0.0  # intensity 0.0 (off) - 1.0 (strong), consistent with grain/haze
    bloom: float = 0.0     # intensity 0.0 (off) - 1.0 (strong)
    grain: float = 0.0
    haze: float = 0.0
    lut_path: str | None = None
    bypass: bool = False

    def to_dict(self) -> dict:
        return dict(
            exposure=self.exposure, contrast=self.contrast, highlights=self.highlights,
            shadows=self.shadows, saturation=self.saturation, temperature=self.temperature,
            tint=self.tint, gamma=self.gamma, sharpen=self.sharpen, denoise=self.denoise,
            vignette=self.vignette, bloom=self.bloom, grain=self.grain, haze=self.haze,
            lut_path=self.lut_path, bypass=self.bypass,
        )

    @classmethod
    def from_dict(cls, d: dict | None) -> "EnhancementSettings":
        d = d or {}
        return cls(**{k: d[k] for k in d if k in cls.__dataclass_fields__})


@dataclass
class StabilizationSettings:
    enabled: bool = False
    preset: str = "balanced"

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "preset": self.preset}

    @classmethod
    def from_dict(cls, d: dict | None) -> "StabilizationSettings":
        d = d or {}
        preset = d.get("preset", "balanced")
        _require(preset in _STABILIZATION_PRESETS, f"unknown stabilization preset '{preset}'")
        return cls(enabled=bool(d.get("enabled", False)), preset=preset)


@dataclass
class FlickerReductionSettings:
    enabled: bool = False
    strength: float = 0.3

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "strength": self.strength}

    @classmethod
    def from_dict(cls, d: dict | None) -> "FlickerReductionSettings":
        d = d or {}
        return cls(enabled=bool(d.get("enabled", False)), strength=float(d.get("strength", 0.3)))


@dataclass
class UpscaleSettings:
    mode: str = "none"
    engine: str = "auto"

    def to_dict(self) -> dict:
        return {"mode": self.mode, "engine": self.engine}

    @classmethod
    def from_dict(cls, d: dict | None) -> "UpscaleSettings":
        d = d or {}
        mode = d.get("mode", "none")
        engine = d.get("engine", "auto")
        _require(mode in _UPSCALE_MODES, f"unknown upscale mode '{mode}'")
        _require(engine in _UPSCALE_ENGINES, f"unknown upscale engine '{engine}'")
        return cls(mode=mode, engine=engine)


@dataclass
class ReframeSettings:
    aspect: str = "9:16"
    focal_point: list[float] = field(default_factory=lambda: [0.5, 0.5])
    mode: str = "center_crop"
    safe_zones: bool = True

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect,
            "focal_point": list(self.focal_point),
            "mode": self.mode,
            "safe_zones": self.safe_zones,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "ReframeSettings":
        d = d or {}
        aspect = d.get("aspect", "9:16")
        mode = d.get("mode", "center_crop")
        _require(aspect in _REFRAME_ASPECTS, f"unknown reframe aspect '{aspect}'")
        _require(mode in _REFRAME_MODES, f"unknown reframe mode '{mode}'")
        return cls(
            aspect=aspect,
            focal_point=list(d.get("focal_point", [0.5, 0.5])),
            mode=mode,
            safe_zones=bool(d.get("safe_zones", True)),
        )


@dataclass
class RIFESettings:
    enabled: bool = False
    target_fps: int | None = None
    strength: float = 0.5

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "target_fps": self.target_fps, "strength": self.strength}

    @classmethod
    def from_dict(cls, d: dict | None) -> "RIFESettings":
        d = d or {}
        return cls(
            enabled=bool(d.get("enabled", False)),
            target_fps=d.get("target_fps"),
            strength=float(d.get("strength", 0.5)),
        )


@dataclass
class ExportSettings:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    video_codec: str = "libx264"
    pix_fmt: str = "yuv420p"
    audio_codec: str = "aac"
    crf: int | None = 20
    bitrate: str | None = None
    faststart: bool = True
    preset_name: str = "instagram_reel"
    hardware_encoder: str | None = None

    def to_dict(self) -> dict:
        return dict(
            width=self.width, height=self.height, fps=self.fps, video_codec=self.video_codec,
            pix_fmt=self.pix_fmt, audio_codec=self.audio_codec, crf=self.crf, bitrate=self.bitrate,
            faststart=self.faststart, preset_name=self.preset_name, hardware_encoder=self.hardware_encoder,
        )

    @classmethod
    def from_dict(cls, d: dict | None) -> "ExportSettings":
        d = d or {}
        return cls(**{k: d[k] for k in d if k in cls.__dataclass_fields__})


EXPORT_PRESETS: dict[str, ExportSettings] = {
    "instagram_reel": ExportSettings(width=1080, height=1920, fps=30, video_codec="libx264",
                                      pix_fmt="yuv420p", audio_codec="aac", crf=20, faststart=True,
                                      preset_name="instagram_reel"),
    "youtube_shorts": ExportSettings(width=1080, height=1920, fps=30, video_codec="libx264",
                                      pix_fmt="yuv420p", audio_codec="aac", crf=20, faststart=True,
                                      preset_name="youtube_shorts"),
    "tiktok": ExportSettings(width=1080, height=1920, fps=30, video_codec="libx264",
                              pix_fmt="yuv420p", audio_codec="aac", crf=20, faststart=True,
                              preset_name="tiktok"),
}


@dataclass
class Recipe:
    schema_version: str = RECIPE_SCHEMA_VERSION
    project_name: str = "untitled"
    media: dict[str, MediaRef] = field(default_factory=dict)
    tracks: list[Track] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    audio: AudioSettings | None = None
    enhancement: EnhancementSettings = field(default_factory=EnhancementSettings)
    stabilization: StabilizationSettings = field(default_factory=StabilizationSettings)
    flicker_reduction: FlickerReductionSettings = field(default_factory=FlickerReductionSettings)
    upscale: UpscaleSettings = field(default_factory=UpscaleSettings)
    reframe: ReframeSettings = field(default_factory=ReframeSettings)
    rife: RIFESettings = field(default_factory=RIFESettings)
    export: ExportSettings = field(default_factory=ExportSettings)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "media": {k: v.to_dict() for k, v in self.media.items()},
            "tracks": [t.to_dict() for t in self.tracks],
            "transitions": [t.to_dict() for t in self.transitions],
            "audio": self.audio.to_dict() if self.audio else None,
            "enhancement": self.enhancement.to_dict(),
            "stabilization": self.stabilization.to_dict(),
            "flicker_reduction": self.flicker_reduction.to_dict(),
            "upscale": self.upscale.to_dict(),
            "reframe": self.reframe.to_dict(),
            "rife": self.rife.to_dict(),
            "export": self.export.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Recipe":
        _require(isinstance(d, dict), "recipe must be a JSON object")
        version = d.get("schema_version", RECIPE_SCHEMA_VERSION)
        _require(
            version.split(".")[0] == RECIPE_SCHEMA_VERSION.split(".")[0],
            f"recipe schema_version '{version}' is incompatible with supported major version "
            f"'{RECIPE_SCHEMA_VERSION.split('.')[0]}.x'",
        )
        media = {k: MediaRef.from_dict(v) for k, v in d.get("media", {}).items()}
        return cls(
            schema_version=version,
            project_name=d.get("project_name", "untitled"),
            media=media,
            tracks=[Track.from_dict(t) for t in d.get("tracks", [])],
            transitions=[Transition.from_dict(t) for t in d.get("transitions", [])],
            audio=AudioSettings.from_dict(d.get("audio")),
            enhancement=EnhancementSettings.from_dict(d.get("enhancement")),
            stabilization=StabilizationSettings.from_dict(d.get("stabilization")),
            flicker_reduction=FlickerReductionSettings.from_dict(d.get("flicker_reduction")),
            upscale=UpscaleSettings.from_dict(d.get("upscale")),
            reframe=ReframeSettings.from_dict(d.get("reframe")),
            rife=RIFESettings.from_dict(d.get("rife")),
            export=ExportSettings.from_dict(d.get("export")),
        )
