"""CLI entry point.

    shorts-render render spec.json --output out.mp4
"""

from __future__ import annotations

import argparse
import json
import sys

from renderer import __version__
from renderer.errors import RendererError
from renderer.runner import run_job
from renderer.schema import VideoSpec


def cmd_render(args: argparse.Namespace) -> int:
    try:
        with open(args.spec, "r", encoding="utf-8") as f:
            spec_dict = json.load(f)
    except FileNotFoundError:
        print(f"error: spec file not found: {args.spec}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: spec file is not valid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        spec = VideoSpec.from_dict(spec_dict)
    except RendererError as exc:
        print(f"error: invalid spec: {exc}", file=sys.stderr)
        return 1

    output_path = args.output or "output.mp4"
    result = run_job(spec, output_path, timeout=args.timeout, verify_output=not args.no_verify)

    report = {
        "job_id": result.job_id,
        "status": result.status,
        "output_path": result.output_path,
        "width": result.width,
        "height": result.height,
        "duration": result.duration,
        "error": result.error,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result.status == "completed" else 2


def cmd_serve(args: argparse.Namespace) -> int:
    from renderer.api.auth import AuthNotConfigured
    from renderer.api.server import run_server

    try:
        run_server(
            host=args.host, port=args.port, db_path=args.db, output_dir=args.output_dir,
            concurrency=args.concurrency, base_url=args.base_url,
        )
    except AuthNotConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shorts-render", description="Local FFmpeg renderer for Reels/Shorts.")
    parser.add_argument("--version", action="version", version=f"shorts-render {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_render = subparsers.add_parser("render", help="Render a video spec JSON file.")
    p_render.add_argument("spec", help="Path to a video spec JSON file.")
    p_render.add_argument("--output", "-o", help="Output MP4 path (default: output.mp4).")
    p_render.add_argument("--timeout", type=float, default=600.0, help="Render timeout in seconds (default 600).")
    p_render.add_argument("--no-verify", action="store_true", help="Skip post-render ffprobe verification.")
    p_render.set_defaults(func=cmd_render)

    p_serve = subparsers.add_parser("serve", help="Run the authenticated HTTP rendering API.")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8080)
    p_serve.add_argument("--db", default="jobs.sqlite3", help="Path to the job-state sqlite3 database.")
    p_serve.add_argument("--output-dir", default="render_output", help="Directory for completed MP4s.")
    p_serve.add_argument("--concurrency", type=int, default=2, help="Max simultaneous ffmpeg renders.")
    p_serve.add_argument("--base-url", default=None, help="Public base URL used in signed download links (default: http://<host>:<port>).")
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
