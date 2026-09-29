# EpicCut Studio (Phase A)

Local-first short-form video editor focused on turning AI-generated
cinematic source video + music into a polished 9:16 Reel/Short/TikTok — no
cloud APIs, no subscription. See `ARCHITECTURE.md`, `FEATURE_MATRIX.md`, and
`IMPLEMENTATION_PLAN.md` for the full design and staged rollout; this file
is just the quick start for what Phase A actually ships: the CLI + FFmpeg
render engine + JSON recipe schema.

## Requirements

- Python 3.11+
- `ffmpeg` / `ffprobe` on `PATH`

## Install (editable, for development)

```bash
cd epiccut-studio
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

## Run the tests

```bash
pytest
```

## CLI usage

### One-off: Auto Finish a single AI clip + music

```bash
epiccut surreal \
  --video source.mp4 \
  --music ambient.mp3 \
  --duration 12 \
  --music-start 60 \
  --preset sacred-temple \
  --output final.mp4
```

Add `--save-recipe recipe.json` to also write out the recipe this command
constructed, so you can hand-edit it and re-render with `epiccut render`.
Add `--dry-run` to print the ffmpeg command without rendering.

### Render an existing recipe

```bash
epiccut render recipe.json --output final.mp4
```

Every recipe is plain JSON (`RECIPE_SCHEMA_VERSION` in
`epiccut/schema/recipe.py`) — the same format the future GUI and HTTP API
will read and write, per `ARCHITECTURE.md`.

## What Phase A does and doesn't do yet

See `FEATURE_MATRIX.md` for the full breakdown. In short: retiming (incl.
the 5.04s→12s "no repeat/concat" case), music trim/fade/volume, a real
FFmpeg render/QA pipeline, and RIFE/Real-ESRGAN *detection* (with clean
fallback) all work today. The full Epic Surreal Auto Finish 15-step
pipeline, visual grading filters, stabilization, flicker reduction, the
PySide6 GUI, and the real RIFE/Real-ESRGAN bodies are staged for Phases B–D.
