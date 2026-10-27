"""VideoSpec -> a concrete ffmpeg argv list.

Always builds an argv **list**, never a shell string — subprocess passes
each element to the OS exactly as-is, so no path or option needs quoting.
User-generated text (Hook/Caption/CTA/subtitle lines) never appears in the
filter-graph string either; see textutil.py for why.
"""

from __future__ import annotations

from dataclasses import dataclass

from renderer.assets import resolve_asset
from renderer.fonts import find_korean_capable_font
from renderer.schema import Scene, TextOverlay, VideoSpec
from renderer.textutil import escape_filtergraph_path, write_text_file


@dataclass
class BuiltCommand:
    argv: list[str]
    expected_duration: float
    expects_audio: bool


def _cover_or_contain_filter(width: int, height: int, fit: str) -> str:
    target_ar = width / height
    if fit == "cover":
        return (
            f"crop='if(gt(iw/ih,{target_ar}),ih*{target_ar},iw)':"
            f"'if(gt(iw/ih,{target_ar}),ih,iw/{target_ar})',"
            f"scale={width}:{height}:flags=lanczos"
        )
    # contain: scale to fit within the frame, then pad to exact size (letterbox).
    return (
        f"scale='if(gt(iw/ih,{target_ar}),{width},-2)':'if(gt(iw/ih,{target_ar}),-2,{height})':flags=lanczos,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
    )


def _text_y_expr(text: TextOverlay, height: int, safe_top: int, safe_bottom: int) -> str:
    """Build the (unquoted-internally) `y` expression. The caller wraps the
    result in single quotes, so literal commas/colons inside — from if(),
    min(), max() — need no backslash-escaping (ffmpeg's filter-string
    quoting treats everything but `'` and `\\` as literal inside quotes)."""
    if text.position == "custom":
        base = str(text.y)
    elif text.position == "top":
        base = f"({safe_top}+40)"
    elif text.position == "center":
        base = "((h-th)/2)"
    else:  # bottom
        base = f"(h-th-{safe_bottom}-60)"

    if text.animation == "slide_up":
        # Slides up into place over 0.4s after `start`, settling at `base`.
        return f"({base})+(60*(1-min(max((t-{text.start})/0.4,0),1)))"
    return base


def _text_alpha_expr(text: TextOverlay) -> str | None:
    if text.animation != "fade":
        return None
    end = text.end if text.end is not None else text.start + 1.0
    fade_dur = min(0.3, max(0.05, (end - text.start) / 2))
    return (
        f"if(lt(t,{text.start + fade_dur}),(t-{text.start})/{fade_dur},"
        f"if(gt(t,{end - fade_dur}),({end}-t)/{fade_dur},1))"
    )


def _drawtext_for_overlay(text: TextOverlay, work_dir: str, font_path: str, width: int, height: int,
                           safe_top: int, safe_bottom: int) -> str:
    text_file = write_text_file(work_dir, text.content)
    end = text.end if text.end is not None else 999999
    opts = [
        f"fontfile='{escape_filtergraph_path(font_path)}'",
        f"textfile='{escape_filtergraph_path(text_file)}'",
        f"fontsize={text.font_size}",
        f"fontcolor={text.color}",
        "borderw=3",
        "bordercolor=black@0.7",
        "x=(w-text_w)/2",
        f"y='{_text_y_expr(text, height, safe_top, safe_bottom)}'",
        f"enable='between(t,{text.start},{end})'",
    ]
    alpha = _text_alpha_expr(text)
    if alpha is not None:
        opts.append(f"alpha='{alpha}'")
    return "drawtext=" + ":".join(opts)


def _drawtext_for_subtitle(sub, work_dir: str, font_path: str, height: int, safe_bottom: int) -> str:
    text_file = write_text_file(work_dir, sub.text)
    opts = [
        f"fontfile='{escape_filtergraph_path(font_path)}'",
        f"textfile='{escape_filtergraph_path(text_file)}'",
        "fontsize=52",
        "fontcolor=white",
        "box=1",
        "boxcolor=black@0.55",
        "boxborderw=18",
        "x=(w-text_w)/2",
        f"y='h-text_h-{safe_bottom}-40'",
        f"enable='between(t,{sub.start},{sub.end})'",
    ]
    return "drawtext=" + ":".join(opts)


def _scene_filters(scene: Scene, media_duration: float, output_width: int, output_height: int, fps: int,
                    work_dir: str, font_path: str, safe_top: int, safe_bottom: int) -> list[str]:
    filters = [_cover_or_contain_filter(output_width, output_height, scene.background.fit)]
    filters.append(f"trim=duration={scene.duration:.6f}")
    filters.append("setpts=PTS-STARTPTS")
    filters.append(f"fps={fps}")
    filters.append("setsar=1")

    for text in scene.texts:
        filters.append(_drawtext_for_overlay(text, work_dir, font_path, output_width, output_height, safe_top, safe_bottom))
    for sub in scene.subtitles:
        filters.append(_drawtext_for_subtitle(sub, work_dir, font_path, output_height, safe_bottom))

    filters.append("format=yuv420p")
    return filters


def build_render_command(spec: VideoSpec, work_dir: str, output_path: str) -> BuiltCommand:
    import shutil

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found on PATH")

    font_path = find_korean_capable_font()
    argv: list[str] = [ffmpeg, "-y"]
    filter_parts: list[str] = []
    video_labels: list[str] = []
    scene_durations: list[float] = []

    for i, scene in enumerate(spec.scenes):
        bg_path = resolve_asset(scene.background.source, work_dir)
        if scene.background.kind == "image":
            argv += ["-loop", "1", "-t", f"{scene.duration:.6f}", "-i", bg_path]
        else:
            argv += ["-stream_loop", "-1", "-t", f"{scene.duration:.6f}", "-i", bg_path]

        filters = _scene_filters(
            scene, scene.duration, spec.output.width, spec.output.height, spec.output.fps,
            work_dir, font_path, spec.safe_zones.top, spec.safe_zones.bottom,
        )
        label = f"v{i}"
        filter_parts.append(f"[{i}:v]{','.join(filters)}[{label}]")
        video_labels.append(label)
        scene_durations.append(scene.duration)

    if len(video_labels) == 1:
        video_out = video_labels[0]
        total_video_duration = scene_durations[0]
    else:
        video_out, total_video_duration = _build_transition_chain(filter_parts, video_labels, scene_durations, spec.scenes)

    if spec.fade_in > 0 or spec.fade_out > 0:
        fade_filters = []
        if spec.fade_in > 0:
            fade_filters.append(f"fade=t=in:st=0:d={spec.fade_in:.6f}")
        if spec.fade_out > 0:
            fade_start = max(0.0, total_video_duration - spec.fade_out)
            fade_filters.append(f"fade=t=out:st={fade_start:.6f}:d={spec.fade_out:.6f}")
        filter_parts.append(f"[{video_out}]{','.join(fade_filters)}[vout]")
        video_out = "vout"
    else:
        filter_parts.append(f"[{video_out}]null[vout]")
        video_out = "vout"

    audio_inputs: list[str] = []
    next_input_index = len(spec.scenes)

    if spec.voiceover is not None:
        vo_path = resolve_asset(spec.voiceover.source, work_dir)
        argv += ["-i", vo_path]
        label = "voice"
        chain = [f"atrim=start={spec.voiceover.start:.6f}", "asetpts=PTS-STARTPTS"]
        if spec.voiceover.volume != 1.0:
            chain.append(f"volume={spec.voiceover.volume:.6f}")
        chain.append(f"apad=whole_dur={total_video_duration:.6f}")
        chain.append(f"atrim=duration={total_video_duration:.6f}")
        filter_parts.append(f"[{next_input_index}:a]{','.join(chain)}[{label}]")
        audio_inputs.append(label)
        next_input_index += 1

    if spec.background_music is not None:
        music_path = resolve_asset(spec.background_music.source, work_dir)
        argv += ["-i", music_path]
        label = "music"
        chain = [f"atrim=start={spec.background_music.start:.6f}", "asetpts=PTS-STARTPTS"]
        if spec.background_music.volume != 1.0:
            chain.append(f"volume={spec.background_music.volume:.6f}")
        if spec.background_music.fade_in > 0:
            chain.append(f"afade=t=in:st=0:d={spec.background_music.fade_in:.6f}")
        if spec.background_music.fade_out > 0:
            fade_start = max(0.0, total_video_duration - spec.background_music.fade_out)
            chain.append(f"afade=t=out:st={fade_start:.6f}:d={spec.background_music.fade_out:.6f}")
        chain.append(f"apad=whole_dur={total_video_duration:.6f}")
        chain.append(f"atrim=duration={total_video_duration:.6f}")
        filter_parts.append(f"[{next_input_index}:a]{','.join(chain)}[{label}]")
        audio_inputs.append(label)
        next_input_index += 1

    expects_audio = len(audio_inputs) > 0
    if expects_audio:
        if len(audio_inputs) == 1:
            filter_parts.append(f"[{audio_inputs[0]}]aresample={spec.output.audio_rate}[aout]")
        else:
            joined = "".join(f"[{lbl}]" for lbl in audio_inputs)
            filter_parts.append(f"{joined}amix=inputs={len(audio_inputs)}:duration=longest:normalize=0,"
                                 f"aresample={spec.output.audio_rate}[aout]")

    argv += ["-filter_complex", ";".join(filter_parts)]
    argv += ["-map", f"[{video_out}]"]
    if expects_audio:
        argv += ["-map", "[aout]"]

    argv += ["-r", str(spec.output.fps)]
    argv += ["-c:v", spec.output.video_codec, "-pix_fmt", spec.output.pix_fmt, "-crf", str(spec.output.crf)]
    if expects_audio:
        argv += ["-c:a", spec.output.audio_codec, "-ar", str(spec.output.audio_rate)]
    argv += ["-movflags", "+faststart"]
    argv += ["-t", f"{total_video_duration:.6f}"]
    argv.append(output_path)

    return BuiltCommand(argv=argv, expected_duration=total_video_duration, expects_audio=expects_audio)


def _build_transition_chain(filter_parts: list[str], labels: list[str], durations: list[float], scenes: list[Scene]) -> tuple[str, float]:
    current_label = labels[0]
    running_duration = durations[0]

    for i in range(1, len(labels)):
        next_label = labels[i]
        transition = scenes[i].transition_in
        out_label = f"x{i}"
        if transition.type == "none":
            filter_parts.append(f"[{current_label}][{next_label}]concat=n=2:v=1:a=0[{out_label}]")
            running_duration = running_duration + durations[i]
        else:
            offset = max(0.0, running_duration - transition.duration)
            xfade_type = "fade" if transition.type == "dissolve" else transition.type
            filter_parts.append(
                f"[{current_label}][{next_label}]xfade=transition={xfade_type}:"
                f"duration={transition.duration:.6f}:offset={offset:.6f}[{out_label}]"
            )
            running_duration = offset + durations[i]
        current_label = out_label

    return current_label, running_duration
