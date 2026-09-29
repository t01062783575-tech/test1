"""EpicCut Studio command-line interface.

    epiccut render recipe.json --output out.mp4
    epiccut surreal --video source.mp4 --music ambient.mp3 --duration 12 \\
        --music-start 60 --preset sacred-temple --output final.mp4

Both subcommands funnel through the exact same recipe -> command_builder ->
runner -> qa path (see ARCHITECTURE.md, section 3): `surreal` just builds a
Recipe in memory first (and can save it with --save-recipe) instead of
reading one from disk.
"""

from __future__ import annotations

import argparse
import json
import sys

from epiccut import __version__
from epiccut.engine.binaries import ffmpeg_available, ffprobe_available
from epiccut.engine.command_builder import build_render_command
from epiccut.engine.probe import probe_media
from epiccut.engine.qa import QAExpectation, expected_codec_name, verify_export
from epiccut.engine.retiming import compute_retiming
from epiccut.engine.runner import run_ffmpeg
from epiccut.errors import EpicCutError
from epiccut.presets.epic_surreal import EPIC_SURREAL_PRESETS, apply_preset_to_recipe
from epiccut.schema.recipe import (
    EXPORT_PRESETS,
    AudioSettings,
    Clip,
    MediaRef,
    Recipe,
    SpeedCurve,
    Track,
)
from epiccut.schema.validate import validate_recipe
from epiccut.utils.paths import ensure_parent_dir


def _check_binaries() -> int | None:
    if not ffmpeg_available():
        print("error: ffmpeg was not found on PATH. Install ffmpeg and try again.", file=sys.stderr)
        return 1
    if not ffprobe_available():
        print("error: ffprobe was not found on PATH. Install ffmpeg (which includes ffprobe) and try again.",
              file=sys.stderr)
        return 1
    return None


def _print_progress(block: dict) -> None:
    out_time = block.get("out_time", "")
    speed = block.get("speed", "")
    if out_time:
        print(f"\r  rendering... {out_time} (speed {speed})", end="", flush=True)


def cmd_render(args: argparse.Namespace) -> int:
    rc = _check_binaries()
    if rc is not None:
        return rc

    try:
        with open(args.recipe, "r", encoding="utf-8") as f:
            recipe_dict = json.load(f)
    except FileNotFoundError:
        print(f"error: recipe file not found: {args.recipe}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: recipe file is not valid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        recipe = Recipe.from_dict(recipe_dict)
        validate_recipe(recipe)
    except EpicCutError as exc:
        print(f"error: invalid recipe: {exc}", file=sys.stderr)
        return 1

    output_path = args.output or "output.mp4"
    ensure_parent_dir(output_path)

    try:
        media_info = {media_id: probe_media(ref.path) for media_id, ref in recipe.media.items()}
        built = build_render_command(recipe, media_info, output_path)
    except EpicCutError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(" ".join(built.argv))
        return 0

    try:
        run_ffmpeg(built.argv, output_path, on_progress=_print_progress)
    except EpicCutError as exc:
        print(f"\nerror: render failed: {exc}", file=sys.stderr)
        return 1
    print()

    report = verify_export(
        output_path,
        QAExpectation(
            duration=built.expected_duration,
            width=built.expected_width,
            height=built.expected_height,
            fps=built.expected_fps,
            video_codec=expected_codec_name(recipe.export.video_codec),
            expect_audio=built.expects_audio,
        ),
    )
    _print_qa_report(report)
    return 0 if report.ok else 2


def _build_surreal_recipe(args: argparse.Namespace) -> Recipe:
    media: dict[str, MediaRef] = {"video": MediaRef(id="video", path=args.video, kind="video")}
    audio = None
    if args.music:
        media["music"] = MediaRef(id="music", path=args.music, kind="audio")
        audio = AudioSettings(
            source_media_id="music",
            start=args.music_start,
            duration=args.duration,
            fade_in=args.music_fade_in,
            fade_out=args.music_fade_out,
            volume=args.music_volume,
            normalize=args.normalize_music,
        )

    clip = Clip(
        id="c0",
        media_id="video",
        track_id="v0",
        source_in=0.0,
        source_out=None,
        timeline_start=0.0,
        speed=SpeedCurve(mode="target_duration", target_duration=args.duration, allow_interpolation=args.allow_rife),
    )
    track = Track(id="v0", kind="video", clips=[clip])

    export = EXPORT_PRESETS[args.export_preset]
    recipe = Recipe(project_name=args.project_name, media=media, tracks=[track], audio=audio, export=export)

    if args.preset:
        recipe = apply_preset_to_recipe(recipe, args.preset)

    return recipe


def cmd_surreal(args: argparse.Namespace) -> int:
    rc = _check_binaries()
    if rc is not None:
        return rc

    recipe = _build_surreal_recipe(args)
    try:
        validate_recipe(recipe)
    except EpicCutError as exc:
        print(f"error: invalid recipe: {exc}", file=sys.stderr)
        return 1

    if args.save_recipe:
        with open(args.save_recipe, "w", encoding="utf-8") as f:
            json.dump(recipe.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"saved recipe to {args.save_recipe}")

    try:
        video_info = probe_media(args.video)
    except EpicCutError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    plan = compute_retiming(video_info.duration, args.duration, allow_interpolation=args.allow_rife)
    print(
        f"retiming: {video_info.duration:.3f}s source -> {args.duration:.3f}s target "
        f"(speed_factor={plan.speed_factor:.4f}, playback_rate={plan.playback_rate:.4f}x)"
    )
    if plan.judder_risk:
        if args.allow_rife:
            print("  judder risk detected: RIFE interpolation requested (renders via plain FFmpeg until Phase D).")
        else:
            print("  judder risk detected: consider --allow-rife for smoother motion once Phase D lands.")

    output_path = args.output or "output.mp4"
    ensure_parent_dir(output_path)

    try:
        media_info = {media_id: probe_media(ref.path) for media_id, ref in recipe.media.items()}
        built = build_render_command(recipe, media_info, output_path, target_duration=args.duration)
    except EpicCutError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(" ".join(built.argv))
        return 0

    try:
        run_ffmpeg(built.argv, output_path, on_progress=_print_progress)
    except EpicCutError as exc:
        print(f"\nerror: render failed: {exc}", file=sys.stderr)
        return 1
    print()

    report = verify_export(
        output_path,
        QAExpectation(
            duration=built.expected_duration,
            width=built.expected_width,
            height=built.expected_height,
            fps=built.expected_fps,
            video_codec=expected_codec_name(recipe.export.video_codec),
            expect_audio=built.expects_audio,
        ),
    )
    _print_qa_report(report)
    return 0 if report.ok else 2


def _print_qa_report(report) -> None:
    if report.ok:
        print(
            f"QA passed: {report.width}x{report.height} @ {report.fps:.2f}fps, "
            f"{report.duration:.2f}s, audio={report.has_audio}, bitrate={report.bit_rate}"
        )
    else:
        print("QA FAILED:", file=sys.stderr)
        for issue in report.issues:
            print(f"  - {issue}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="epiccut", description="EpicCut Studio — local short-form video editor.")
    parser.add_argument("--version", action="version", version=f"epiccut {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_render = subparsers.add_parser("render", help="Render a recipe JSON file.")
    p_render.add_argument("recipe", help="Path to a recipe JSON file.")
    p_render.add_argument("--output", "-o", help="Output MP4 path (default: output.mp4).")
    p_render.add_argument("--dry-run", action="store_true", help="Print the ffmpeg command instead of running it.")
    p_render.set_defaults(func=cmd_render)

    p_surreal = subparsers.add_parser("surreal", help="Epic Surreal Auto Finish: one AI clip + music -> a polished Reel.")
    p_surreal.add_argument("--video", required=True, help="Path to the source AI-generated video.")
    p_surreal.add_argument("--music", help="Path to a music track.")
    p_surreal.add_argument("--duration", type=float, default=12.0, help="Target output duration in seconds (default 12).")
    p_surreal.add_argument("--music-start", type=float, default=0.0, help="Offset into the music track, seconds.")
    p_surreal.add_argument("--music-fade-in", type=float, default=0.5)
    p_surreal.add_argument("--music-fade-out", type=float, default=1.0)
    p_surreal.add_argument("--music-volume", type=float, default=1.0)
    p_surreal.add_argument("--normalize-music", action="store_true")
    p_surreal.add_argument("--preset", choices=sorted(EPIC_SURREAL_PRESETS.keys()), help="Epic Surreal look preset.")
    p_surreal.add_argument("--export-preset", choices=sorted(EXPORT_PRESETS.keys()), default="instagram_reel")
    p_surreal.add_argument("--project-name", default="epic-surreal")
    p_surreal.add_argument("--allow-rife", action="store_true", help="Permit RIFE interpolation when judder risk is detected (no-op until Phase D if RIFE isn't installed).")
    p_surreal.add_argument("--save-recipe", help="Also write the constructed recipe to this JSON path.")
    p_surreal.add_argument("--output", "-o", help="Output MP4 path (default: output.mp4).")
    p_surreal.add_argument("--dry-run", action="store_true", help="Print the ffmpeg command instead of running it.")
    p_surreal.set_defaults(func=cmd_surreal)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ncancelled", file=sys.stderr)
        return 130
    except EpicCutError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
