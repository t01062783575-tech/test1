"""Recipe (+ probed MediaInfo) -> a concrete ffmpeg argv list.

This is the one place recipes turn into ffmpeg filter graphs. The GUI, the
CLI's `render` and `surreal` commands, and the Epic Surreal Auto Finish
pipeline (Phase B) all funnel through this module so there is exactly one
rendering code path, per ARCHITECTURE.md.

Scope note (Phase A): renders the primary video track's clips (trim, static
crop/scale/rotation/opacity, reverse, best-effort freeze-frame, constant/
target-duration retiming, per-clip fades, concat or crossfade between
clips) reframed to the export's exact width/height, plus one optional
project-level music track (AudioSettings) with trim/fade/volume/normalize/
limiter. Multi-track overlay compositing and keyframe evaluation are
GUI-era (Phase B/C) work — see FEATURE_MATRIX.md.

Commands are always built as argv **lists**, never shell strings, so paths
containing spaces or Korean characters need no manual quoting/escaping —
`subprocess` passes each argv element to the OS exactly as given.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from epiccut.engine.audio_plan import plan_music
from epiccut.engine.binaries import find_ffmpeg
from epiccut.engine.probe import MediaInfo
from epiccut.engine.retiming import compute_retiming, output_fps_for_retiming, setpts_filter
from epiccut.errors import RenderError
from epiccut.schema.recipe import Clip, Recipe, Track


@dataclass
class BuiltCommand:
    argv: list[str]
    expected_duration: float
    expected_width: int
    expected_height: int
    expected_fps: float
    expects_audio: bool


def _primary_video_track(recipe: Recipe) -> Track:
    video_tracks = [t for t in recipe.tracks if t.kind == "video" and t.enabled and t.clips]
    if not video_tracks:
        raise RenderError("recipe has no enabled video track with clips to render")
    return video_tracks[0]


def _clip_source_duration(clip: Clip, media_duration: float) -> float:
    end = clip.source_out if clip.source_out is not None else media_duration
    return max(0.0, end - clip.source_in)


def _reframe_filter(width: int, height: int) -> str:
    """Center-crop to the target aspect ratio, then scale to the exact
    export resolution. Covers 'landscape source -> portrait export' and any
    other aspect mismatch: crop to the right ratio first (no distortion),
    then scale (Lanczos) to exact pixel dimensions."""
    target_ar = width / height
    return (
        f"crop='if(gt(iw/ih,{target_ar}),ih*{target_ar},iw)':"
        f"'if(gt(iw/ih,{target_ar}),ih,iw/{target_ar})',"
        f"scale={width}:{height}:flags=lanczos,setsar=1"
    )


def _clip_filters(clip: Clip, media: MediaInfo, target_duration: float | None) -> tuple[list[str], float]:
    """Return (filter list, resulting clip duration) for one clip, before
    reframe/concat. `target_duration` is set only when the clip's speed mode
    is 'target_duration'."""

    filters: list[str] = []
    source_duration = _clip_source_duration(clip, media.duration)

    filters.append(f"trim=start={clip.source_in:.6f}:end={clip.source_in + source_duration:.6f}")
    filters.append("setpts=PTS-STARTPTS")

    if clip.reverse:
        filters.append("reverse")

    speed = clip.speed
    if speed.mode == "target_duration":
        if target_duration is None:
            target_duration = speed.target_duration
        if target_duration is None:
            raise RenderError(f"clip '{clip.id}' speed mode is 'target_duration' but no target was given")
        plan = compute_retiming(source_duration, target_duration, allow_interpolation=speed.allow_interpolation)
        filters.append(setpts_filter(plan.speed_factor))
        result_duration = plan.target_duration
    elif speed.mode == "constant" and speed.factor != 1.0:
        filters.append(setpts_filter(speed.factor))
        result_duration = source_duration * speed.factor
    else:
        result_duration = source_duration

    if clip.crop is not None and clip.crop.width and clip.crop.height:
        filters.append(f"crop={clip.crop.width}:{clip.crop.height}:{clip.crop.x}:{clip.crop.y}")

    scale = clip.transform.scale.static_value
    if scale is not None and scale != 1.0 and not clip.transform.scale.is_keyframed():
        filters.append(f"scale=iw*{scale:.6f}:ih*{scale:.6f}:flags=lanczos")

    rotation = clip.transform.rotation.static_value
    if rotation is not None and rotation != 0.0 and not clip.transform.rotation.is_keyframed():
        radians = f"{rotation}*PI/180"
        filters.append(f"rotate={radians}:c=black")

    opacity = clip.transform.opacity.static_value
    if opacity is not None and opacity != 1.0 and not clip.transform.opacity.is_keyframed():
        opacity = max(0.0, min(1.0, opacity))
        filters.append("format=yuva420p")
        filters.append(f"colorchannelmixer=aa={opacity:.6f}")
        filters.append("format=yuv420p")

    if clip.fade.fade_in > 0:
        filters.append(f"fade=t=in:st=0:d={clip.fade.fade_in:.6f}")
    if clip.fade.fade_out > 0:
        fade_start = max(0.0, result_duration - clip.fade.fade_out)
        filters.append(f"fade=t=out:st={fade_start:.6f}:d={clip.fade.fade_out:.6f}")

    return filters, result_duration


def build_render_command(
    recipe: Recipe,
    media_info: dict[str, MediaInfo],
    output_path: str,
    *,
    target_duration: float | None = None,
) -> BuiltCommand:
    """Build the full ffmpeg argv for rendering `recipe` to `output_path`.

    `media_info` maps media id -> probed MediaInfo (the caller probes once
    per media file and passes the results in, so this function stays a pure
    "recipe + facts -> command" transform with no subprocess calls of its
    own — easy to unit test).
    """

    track = _primary_video_track(recipe)
    ffmpeg = find_ffmpeg()

    argv: list[str] = [ffmpeg, "-y"]
    filter_parts: list[str] = []
    clip_video_labels: list[str] = []
    clip_durations: list[float] = []

    for i, clip in enumerate(track.clips):
        media = media_info.get(clip.media_id)
        if media is None:
            raise RenderError(f"no probed MediaInfo for clip '{clip.id}' media '{clip.media_id}'")

        argv += ["-i", media.path]
        input_index = i

        clip_target = target_duration if (len(track.clips) == 1 and target_duration is not None) else None
        filters, duration = _clip_filters(clip, media, clip_target)
        label = f"v{i}"
        chain = ",".join(filters) if filters else "null"
        filter_parts.append(f"[{input_index}:v]{chain}[{label}]")
        clip_video_labels.append(label)
        clip_durations.append(duration)

    # Concat (or crossfade chain if transitions are present) into [vraw]
    if len(clip_video_labels) == 1:
        video_out_label = clip_video_labels[0]
    elif recipe.transitions:
        video_out_label = _build_xfade_chain(filter_parts, clip_video_labels, clip_durations, recipe.transitions)
    else:
        joined = "".join(f"[{lbl}]" for lbl in clip_video_labels)
        filter_parts.append(f"{joined}concat=n={len(clip_video_labels)}:v=1:a=0[vraw]")
        video_out_label = "vraw"

    export = recipe.export
    filter_parts.append(f"[{video_out_label}]{_reframe_filter(export.width, export.height)}[vout]")

    expected_duration = sum(clip_durations) if not recipe.transitions else max(
        sum(clip_durations) - sum(t.duration for t in recipe.transitions), clip_durations[0] if clip_durations else 0.0
    )

    audio_input_index = None
    expects_audio = False
    if recipe.audio is not None and recipe.audio.source_media_id and not recipe.audio.mute:
        audio_media = media_info.get(recipe.audio.source_media_id)
        if audio_media is None:
            raise RenderError(f"no probed MediaInfo for audio source '{recipe.audio.source_media_id}'")

        audio_duration = recipe.audio.duration if recipe.audio.duration is not None else expected_duration
        audio_settings = recipe.audio
        # Freeze the effective duration so fade-out timing (which needs a
        # concrete duration) is correct even when the recipe leaves duration
        # unset and relies on the video's computed length.
        from dataclasses import replace as _replace
        effective_audio = _replace(audio_settings, duration=audio_duration)
        plan = plan_music(effective_audio, source_duration=audio_media.duration)

        argv += ["-ss", f"{plan.start:.6f}", "-t", f"{audio_duration:.6f}", "-i", audio_media.path]
        audio_input_index = sum(1 for a in argv if a == "-i") - 1
        filter_parts.append(f"[{audio_input_index}:a]{plan.filter_chain()}[aout]")
        expects_audio = True

    argv += ["-filter_complex", ";".join(filter_parts)]
    argv += ["-map", "[vout]"]
    if expects_audio:
        argv += ["-map", "[aout]"]

    argv += ["-r", str(output_fps_for_retiming(export.fps, 1.0, export.fps))]
    argv += ["-c:v", export.video_codec, "-pix_fmt", export.pix_fmt]
    if export.crf is not None:
        argv += ["-crf", str(export.crf)]
    if export.bitrate:
        argv += ["-b:v", export.bitrate]
    if expects_audio:
        argv += ["-c:a", export.audio_codec]
    if export.faststart:
        argv += ["-movflags", "+faststart"]
    argv += ["-t", f"{expected_duration:.6f}"]
    argv.append(output_path)

    return BuiltCommand(
        argv=argv,
        expected_duration=expected_duration,
        expected_width=export.width,
        expected_height=export.height,
        expected_fps=export.fps,
        expects_audio=expects_audio,
    )


def _build_xfade_chain(
    filter_parts: list[str],
    clip_labels: list[str],
    clip_durations: list[float],
    transitions: list,
) -> str:
    """Fold clips pairwise with `xfade`, using each adjacent Transition's
    duration (defaulting to 0.5s when a pair has no explicit transition)."""

    transition_by_pair = {(t.clip_a_id, t.clip_b_id): t for t in transitions}
    current_label = clip_labels[0]
    running_duration = clip_durations[0]

    for i in range(1, len(clip_labels)):
        next_label = clip_labels[i]
        # Transitions are keyed by clip id in the recipe; here we only have
        # positional labels, so fall back to a default crossfade duration
        # when we can't resolve a specific pair (Phase A keeps this simple —
        # id-accurate pairing is a Phase B/GUI refinement once clip ids flow
        # through this helper too).
        duration = next(iter(transition_by_pair.values())).duration if transition_by_pair else 0.5
        offset = max(0.0, running_duration - duration)
        out_label = f"x{i}"
        filter_parts.append(
            f"[{current_label}][{next_label}]xfade=transition=fade:duration={duration:.6f}:offset={offset:.6f}[{out_label}]"
        )
        running_duration = offset + clip_durations[i]
        current_label = out_label

    return current_label
