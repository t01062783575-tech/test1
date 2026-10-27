# shorts-renderer (Phase 1 + 2)

Local-first FFmpeg rendering service for automated Instagram Reels /
YouTube Shorts — a real 1080×1920 alternative to Creatomate's free-plan
270×480 limit. See `PHASE3_DESIGN.md` for the (not-yet-implemented) Make.com
integration design and hosting-cost evaluation.

## Requirements

- Python 3.11+
- `ffmpeg` / `ffprobe` on `PATH`
- A Korean-capable font, e.g. `apt install fonts-noto-cjk` (Debian/Ubuntu)

## Install

```bash
cd shorts-renderer
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt   # for tests
```

## Run the tests

```bash
pytest
```

37 tests, including real ffmpeg renders (not mocked) verified with ffprobe —
not just schema/logic unit tests.

## Render a sample

```bash
shorts-render render samples/sample_spec.json --output out.mp4
```

Prints a JSON job report (`job_id`, `status`, `width`, `height`, `duration`,
`error`) to stdout and structured JSON log lines to stderr.

## Video spec format

See `samples/sample_spec.json` for a worked 3-scene example (hook → body →
CTA, with fades, a crossfade transition, animated text, burned-in
subtitles, and mixed voiceover + background music). Key shape:

```json
{
  "job_id": "optional — a uuid4 is generated if omitted",
  "output": { "width": 1080, "height": 1920, "fps": 30 },
  "safe_zones": { "top": 180, "bottom": 260 },
  "fade_in": 0.4, "fade_out": 0.6,
  "voiceover": { "source": "path-or-https-url", "volume": 1.0 },
  "background_music": { "source": "...", "volume": 0.15, "fade_in": 0.5, "fade_out": 1.0 },
  "scenes": [
    {
      "duration": 4.0,
      "background": { "source": "...", "kind": "image", "fit": "cover" },
      "transition_in": { "type": "fade", "duration": 0.5 },
      "texts": [{ "content": "...", "position": "top", "animation": "fade", "start": 0.2, "end": 3.8 }],
      "subtitles": [{ "text": "...", "start": 0.3, "end": 3.8 }]
    }
  ]
}
```

`background.source` and `voiceover`/`background_music`'s `source` accept
either a local file path or an `http(s)://` URL (downloaded on the fly) —
matching how assets already flow through the Make pipeline today
(Backblaze/Cloudinary URLs).

## Security notes (Phase 2)

- Every ffmpeg invocation is an **argv list**, never a shell string — see
  `renderer/runner.py`. There is no shell anywhere in this codebase.
- User-generated text (Hook/Caption/CTA/subtitle lines) is **never**
  interpolated into an ffmpeg filter string. Each piece of text is written
  to its own temp file and referenced via `drawtext=textfile=<our-own-path>`
  — see `renderer/textutil.py` for why this eliminates filter-injection risk
  entirely, with a test (`tests/test_textutil_escaping.py`) that throws
  shell-metacharacter and command-substitution payloads at it and asserts
  they never reach the command line.
- Every job gets a unique `job_id` (caller-supplied or `uuid4`), deterministic
  output settings (fixed codec/pix_fmt/faststart), a render timeout, and
  guaranteed temp-directory cleanup (success, failure, or timeout).

## What's real vs. not yet built

**Built and tested with a real render** (this change): scenes, backgrounds
(image or looped video, cover/contain fit), animated text (fade/slide_up),
burned-in subtitles with a readable background box, fades, one crossfade/
dissolve transition type, voiceover + background music mixing with fades/
volume, safe zones, Korean+English text via Noto Sans CJK, job IDs,
timeout + cleanup, structured logs, ffprobe verification.

**Not yet built** (see `PHASE3_DESIGN.md`): the actual HTTP `/render`
endpoint, Make scenario wiring, cloud/VPS deployment, asset upload to a
public URL. Phase 1/2 ship the renderer itself and prove it end-to-end
locally; Phase 3 is a design only, per the brief.
