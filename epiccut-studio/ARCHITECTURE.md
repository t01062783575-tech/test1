# EpicCut Studio — Architecture

## 0. Context from repository inspection

This repository (`t01062783575-tech/test1`) is otherwise a collection of unrelated
Next.js marketing landing pages (root app + `freelancer-expense-landing/`) and a
separate Python research tool (`research-collector/`, on a different branch). None
of that is reusable for a desktop video editor — different language, different
runtime, different domain. EpicCut Studio is therefore a **new, self-contained
Python project** living at `epiccut-studio/` at the repo root, with its own
dependency manifest and test suite. It does not depend on anything in the Next.js
apps, and nothing in this repo currently duplicates its functionality.

Environment note: this container ships Python 3.11.15 and no system `ffmpeg`.
`ffmpeg`/`ffprobe` 6.1.1 were installed via `apt-get` for this session so Phase A
could be built and tested against a real binary rather than mocks alone. A fresh
machine running EpicCut Studio will need `ffmpeg` on `PATH`; the CLI checks for
it at startup and fails with a clear message rather than a stack trace if it's
missing.

## 1. Goals and non-goals (from spec)

- Local-first, no cloud APIs, no subscription.
- FFmpeg is the render engine; Python is the app language; PySide6 is the
  eventual GUI (Phase C).
- Every GUI operation must be representable as a JSON "recipe". The recipe is
  the single source of truth — **GUI state is never authoritative**, only a
  view onto a recipe that can equally be produced by the CLI or a future HTTP
  API.
- No social publishing. No watermark removal (detection-only, opt-in warning).
- AI modules (RIFE, Real-ESRGAN, Whisper) are optional adapters the core engine
  must run correctly without.

## 2. Top-level module layout

```
epiccut-studio/
  ARCHITECTURE.md         (this file)
  FEATURE_MATRIX.md        feature x phase x status tracking
  IMPLEMENTATION_PLAN.md   staged plan, phase gates
  README.md                quick start / CLI usage
  pyproject.toml           packaging + pytest config
  requirements.txt         runtime deps (Phase A: none beyond stdlib)
  requirements-dev.txt     pytest
  epiccut/
    __init__.py             package version
    cli.py                  argparse entry point: `epiccut render`, `epiccut surreal`
    errors.py               typed exception hierarchy
    schema/
      __init__.py
      recipe.py              versioned recipe dataclasses + to_dict/from_dict
      validate.py            structural + semantic validation, raises RecipeError
    engine/
      __init__.py
      binaries.py            locate/verify ffmpeg, ffprobe on PATH
      probe.py                ffprobe wrapper -> MediaInfo
      retiming.py             speed-factor / judder-risk calculation (pure math)
      audio_plan.py            music trim/fade/volume -> filter graph (pure)
      command_builder.py      recipe (+ MediaInfo) -> concrete ffmpeg argv list
      runner.py                subprocess execution, cancellation, progress
      qa.py                    post-export ffprobe-based verification
    adapters/
      __init__.py
      base.py                  OptionalAdapter protocol: is_available(), reason()
      rife.py                  RIFE detection + stub interpolate() (Phase D body)
      real_esrgan.py           Real-ESRGAN detection + stub upscale() (Phase D body)
    presets/
      __init__.py
      epic_surreal.py          Sacred Temple / Cosmic Monument / Liminal Cathedral /
                                Dream Landscape preset recipes (data, not code)
    utils/
      __init__.py
      paths.py                 safe path handling (spaces, Korean, argv-list only,
                                never shell=True / shell-quoted strings)
      tempdirs.py              context-managed temp dirs, guaranteed cleanup
  tests/
    conftest.py
    fixtures/                  tiny generated test clips (created at test time,
                                not checked in as binaries)
    test_retiming.py
    test_audio_plan.py
    test_recipe_schema.py
    test_paths.py
    test_adapters_missing.py
    test_cli_surreal.py
    test_qa.py
    test_runner_cancel_cleanup.py
```

## 3. The recipe is the source of truth

Every capability the GUI (Phase C) will eventually expose must already exist as
a field in the JSON recipe schema (`epiccut/schema/recipe.py`,
`RECIPE_SCHEMA_VERSION`). The desktop GUI, the CLI, and the future HTTP API are
three different *front ends* that all read and write the same recipe format and
call the same `engine.command_builder` / `engine.runner` code. Concretely:

- `epiccut render recipe.json` loads a recipe from disk and renders it.
- `epiccut surreal --video ... --music ... --preset sacred-temple ...` is sugar
  that **constructs a recipe in memory** (and can dump it with `--save-recipe`)
  before handing it to the exact same render path `render` uses. It never has
  a separate rendering code path.
- A later PySide6 GUI action (e.g. dragging a trim handle) will mutate the same
  recipe object and call the same renderer for preview/export.

This is why Phase A implements the recipe schema and the `surreal` command's
recipe-construction step even though the GUI doesn't exist yet: it is the
contract the GUI will be built against.

## 4. Retiming without repeat/concat (the 5.04s → 12s case)

`engine/retiming.py` is pure math, independent of ffmpeg:

```
speed_factor = target_duration / source_duration   # > 1 means slow down
```

This factor becomes an ffmpeg `setpts=<speed_factor>*PTS` filter on the video
stream — a single continuous timestretch, never a loop or concat. A factor
this extreme (5.04s → 12s is `2.381x` slowdown) is flagged as
`judder_risk = True` when it exceeds a configurable threshold (default 1.6x
speed change in either direction), which is what the Epic Surreal Auto Finish
pipeline and the `--preset epic-surreal-smooth` flag use to *recommend*
(never silently force) RIFE frame interpolation. Frame rate is recalculated so
motion stays smooth at the source's native fps unless interpolation raises it.

## 5. Optional adapters (RIFE / Real-ESRGAN / Whisper)

`adapters/base.py` defines a minimal protocol:

```python
class OptionalAdapter(Protocol):
    def is_available(self) -> bool: ...
    def unavailable_reason(self) -> str | None: ...
```

`engine/command_builder.py` and the Auto Finish pipeline (Phase B) only ever
call an adapter after checking `is_available()`; when it's `False` they log a
one-line notice and fall back to the pure-FFmpeg path. **No code path raises
or crashes because RIFE/Real-ESRGAN/Whisper are absent** — Phase A's
`test_adapters_missing.py` asserts this directly by monkeypatching
`is_available` to `False` and confirming the render still succeeds.

## 6. Quality assurance

`engine/qa.py` runs `ffprobe -print_format json -show_format -show_streams` on
every export and checks, against the recipe's expected output spec:

- file exists and is non-empty
- `|actual_duration - expected_duration| <= 0.1s`
- width/height match
- frame rate matches (within rounding)
- video codec matches
- audio stream present iff recipe requested audio
- bitrate > 0
- frame count > 0 (via `nb_read_frames`/duration×fps sanity check)
- audio and video stream durations agree within tolerance

This is a library function (`qa.verify_export`), callable from the CLI, the
GUI, and tests alike — not a CLI-only afterthought.

## 7. Cancellation and cleanup

`engine/runner.py` runs ffmpeg as a subprocess and accepts a
`threading.Event`-based cancel token; on cancellation it terminates the
subprocess and lets `utils/tempdirs.py`'s context manager remove partial
output and temp frames. Every temp directory used anywhere in the engine goes
through that one context manager so cleanup is guaranteed via `finally`, not
duplicated ad hoc in each call site.

## 8. Phases (see IMPLEMENTATION_PLAN.md for detail)

| Phase | Content |
|---|---|
| A | CLI + FFmpeg engine + recipe schema + tests **(this change)** |
| B | Epic Surreal Auto Finish pipeline |
| C | PySide6 GUI + preview + timeline |
| D | RIFE / Real-ESRGAN real adapter bodies |
| E | Whisper / captions / silence tools |

Each phase's tests must pass before the next phase starts, per the requested
development procedure.
