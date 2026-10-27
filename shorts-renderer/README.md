# shorts-renderer (Phase 1 + 2 + 3 API)

Local-first FFmpeg rendering service for automated Instagram Reels /
YouTube Shorts — a real 1080×1920 alternative to Creatomate's free-plan
270×480 limit. See `PHASE3_DESIGN.md` for the Make.com integration (the
HTTP API below is implemented and proven; the Make-scenario side of it is
still a design, not yet applied to any live scenario) and hosting-cost
evaluation.

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

66 tests, including real ffmpeg renders (not mocked) verified with ffprobe,
and real HTTP requests against a real running server — not just schema/logic
unit tests.

## Render a sample

```bash
shorts-render render samples/sample_spec.json --output out.mp4
```

Prints a JSON job report (`job_id`, `status`, `width`, `height`, `duration`,
`error`) to stdout and structured JSON log lines to stderr.

## HTTP API (Phase 3)

```bash
export SHORTS_RENDERER_API_KEY="<long random value>"   # required; server refuses to start without it
shorts-render serve --port 8080 --db jobs.sqlite3 --output-dir render_output --concurrency 2
```

```bash
# Submit a job (job_id optional — a stable one makes retries idempotent)
curl -X POST http://127.0.0.1:8080/render \
  -H "Authorization: Bearer $SHORTS_RENDERER_API_KEY" -H "Content-Type: application/json" \
  --data-binary @samples/sample_spec.json
# -> {"job_id": "...", "status": "queued", "created": true}

# Poll status
curl http://127.0.0.1:8080/jobs/<job_id> -H "Authorization: Bearer $SHORTS_RENDERER_API_KEY"

# Once status is "completed", mint a short-lived signed download link
curl http://127.0.0.1:8080/jobs/<job_id>/signed-url -H "Authorization: Bearer $SHORTS_RENDERER_API_KEY"
# -> {"url": "http://.../jobs/<job_id>/output?exp=...&sig=...", "expires_at": ...}
curl -o out.mp4 "<that url>"   # no Authorization header needed — this is what Make's http:DownloadFile uses
```

Full route list, auth model, and the Make-side wiring design are in
`PHASE3_DESIGN.md`.

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
- The HTTP API (`renderer/api/`) adds: Bearer-token auth on every route
  except `/healthz` and a validly-signed output link (the server refuses to
  start with no API key configured — `AuthNotConfigured`); a bounded
  `ThreadPoolExecutor` (`--concurrency`) capping simultaneous ffmpeg
  processes; a request body size cap; and idempotent `job_id`-keyed
  submission — re-POSTing the same `job_id` returns the existing job's
  state (`HTTP 200`, `created: false`) instead of starting a second render.

## What's real vs. not yet built

**Built and tested with a real render, including over HTTP** (this change
and the one before it): scenes, backgrounds (image or looped video, cover/
contain fit), animated text (fade/slide_up), burned-in subtitles with a
readable background box, fades, one crossfade/dissolve transition type,
voiceover + background music mixing with fades/volume, safe zones, Korean+
English text via Noto Sans CJK, job IDs, timeout + cleanup, structured logs,
ffprobe verification, and now: the authenticated async HTTP API itself
(`POST /render`, `GET /jobs/{id}`, signed download URLs, idempotent retries,
concurrency limits), proven with a real server process + `curl` + an
independent `ffprobe` check, not just pytest.

**Not yet built** (see `PHASE3_DESIGN.md`): anything on the Make.com side
(no scenario was modified), deployment to a host Make can actually reach
(this was proven against `localhost` only), and uploading output to a
separate public bucket — the current `/output` endpoint serves the file
directly from this service rather than a CDN.
