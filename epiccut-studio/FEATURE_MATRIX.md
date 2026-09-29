# EpicCut Studio — Feature Matrix

Status legend: `done` (implemented + tested this phase) · `stub` (interface
exists, real body deferred to listed phase) · `planned` (not started, tracked
for listed phase).

## Phase A — CLI + FFmpeg engine + recipe schema + tests

| Feature | Status | Notes |
|---|---|---|
| Versioned JSON recipe schema (media/timeline/clips/trims/transforms/keyframes/speed/transitions/audio/effects/enhancement flags/export) | done | `epiccut/schema/recipe.py`, `RECIPE_SCHEMA_VERSION = "0.1.0"` |
| Recipe validation (structural + semantic) | done | `epiccut/schema/validate.py` |
| ffprobe media inspection | done | `epiccut/engine/probe.py` |
| Retiming calculation (constant speed, no repeat/concat) | done | `epiccut/engine/retiming.py` |
| Judder-risk flag for extreme retiming | done | threshold-based, feeds RIFE recommendation only |
| Speed curves (non-constant) | planned (B) | schema field exists; engine only builds constant-speed filters in A |
| Music trim/offset/fade/volume plan | done | `epiccut/engine/audio_plan.py` |
| Command builder (recipe → ffmpeg argv) | done | trims, crop/transform, opacity, fades, crossfade-count-1 case, audio mix |
| Subprocess runner with cancellation | done | `epiccut/engine/runner.py` |
| Guaranteed temp-file cleanup | done | `epiccut/utils/tempdirs.py` |
| Post-export QA via ffprobe | done | `epiccut/engine/qa.py` |
| CLI: `epiccut render recipe.json` | done | |
| CLI: `epiccut surreal --video --music --duration --music-start --preset --output` | done | builds a recipe in-memory, optional `--save-recipe` |
| Epic Surreal presets (data) | done (data only) | Sacred Temple grade values defined; grading *filters* land in Phase B |
| RIFE adapter | stub | `is_available()` real (checks PATH/config); `interpolate()` raises `NotImplementedError` until Phase D |
| Real-ESRGAN adapter | stub | same pattern |
| Provider-watermark detection warning | planned (B) | requires frame sampling; not in A |
| Keyframe engine (position/scale/rotation/opacity/volume, 4 interpolation modes) | schema done, engine planned (B/C) | keyframes serialize now; evaluating them into per-frame filters is a GUI/preview-era concern |
| Stabilization (minimal/balanced/strong) | planned (D-ish, needs vidstab) | schema field reserved |
| Flicker reduction | planned (B) | |
| Visual enhancement (exposure/contrast/.../denoise) + effects (vignette/bloom/grain/haze/LUT) | planned (B) | schema fields reserved, bypassable by design |
| Upscaling (Real-ESRGAN / FFmpeg fallback) | planned (D for real-ESRGAN; FFmpeg lanczos fallback trivial, tracked B) | |
| Auto Reframe (9:16/1:1/4:5/16:9, manual focal point, center crop, safe zones) | planned (B) | architecture leaves room for subject-tracking later, per spec |
| Audio: EQ/compressor/limiter/ducking | planned (B) | normalize + fade + volume covered in A |
| Beat analysis / "align climax to end" | planned (B) | needs a local beat-detection lib |
| Epic Surreal Auto Finish full pipeline (steps 1–15) | planned (B) | Phase A ships the pieces it's built from (probe, retiming, audio plan, command builder, QA); B wires them into the 15-step pipeline + grading/bloom/vignette/grain |
| Still-image Ken Burns mode | planned (B) | |
| Whisper transcription / captions / silence tools | planned (E), disabled by default | |
| Export presets (Reel/Shorts/TikTok 1080x1920 30fps H.264 yuv420p AAC faststart) | done | `epiccut/schema/recipe.py::EXPORT_PRESETS` |
| Bitrate/CRF control, hw encoder selection | done (CRF/bitrate); hw encoder selection stub | hw encoder probing needs per-machine detection, deferred to C |
| Proxy preview (360p/540p) + caching | planned (C) | needs GUI/preview loop |
| Batch queue (pending/processing/completed/failed) | planned (C) | |
| Local HTTP API | planned (later, per spec "do not overbuild first") | |
| PySide6 GUI, timeline, undo/redo | planned (C) | |

## Tests shipped in Phase A

| Test | Covers |
|---|---|
| `test_retiming.py` | 5.04s → 12s factor math, judder-risk threshold, edge cases (zero/negative duration) |
| `test_audio_plan.py` | 12s music extraction, fades, volume, invalid start/duration |
| `test_recipe_schema.py` | round-trip serialization incl. keyframes, invalid-input rejection, missing-audio recipe |
| `test_paths.py` | argv-list construction with spaces and Korean characters in paths |
| `test_adapters_missing.py` | RIFE/Real-ESRGAN absent → `is_available() is False`, engine falls back without raising |
| `test_cli_surreal.py` | end-to-end `epiccut surreal` on a generated portrait/landscape sample, incl. landscape→portrait crop |
| `test_qa.py` | `qa.verify_export` against a real rendered file (duration/dims/fps/codec/audio/bitrate checks) |
| `test_runner_cancel_cleanup.py` | cancellation stops the subprocess; temp dir is removed even when the run raises |

Not yet covered in Phase A (explicitly deferred, tracked so they aren't
forgotten): interrupted-render *resume* (only detection of an incomplete
render marker is implemented in A; actual resume logic is a Phase B/C
concern once the runner has a real progress/checkpoint model).
