# Phase 3 — Make.com Integration Design (not implemented)

This is a design only, per the brief ("Do not modify Make yet"). Nothing in
this document has been applied to any live Make scenario, connection, or
data store record — the two scenarios and the data store described below
were inspected read-only to ground this design in the real pipeline.

## What the existing pipeline actually expects (inspected, read-only)

- Data store **153940** ("My data store", structure `Instagram_Reels_Structure`,
  11 records) is the single source of truth both the Instagram and YouTube
  scenarios poll. Relevant fields already exist on every record: `Render_URL`,
  `Render_Width`, `Render_Height`, `Render_ID`, `Render_Requested_At`,
  `Error_Note`, `Status` / `YT_Status`, `Audit_Flag`.
- **Instagram Reels PUBLISH B-prime** (scenario 6793356) only publishes a
  record when, among other conditions, `Render_Width == 1080` AND
  `Render_Height == 1920` (exact match, not "at least"). This is exactly why
  Creatomate's free-plan 270×480 output currently blocks real publishing —
  records render, but never pass this eligibility filter, confirmed by the
  gate using `number:equal`, not `number:greaterOrEqual`.
- **YouTube Shorts Private Upload C** (scenario 6793516) has the same
  1080×1920 gate for `Audit_Flag != "TEST"` records, downloads `Render_URL`
  directly via `http:DownloadFile`, and uploads it to YouTube as a private
  video. A `TEST`/`TEST_READY` bypass already exists and was used for a real
  end-to-end pipeline test (record `PIPE-TEST-001`, which has `YT_Video_ID`
  set) — so **this renderer's `Render_URL` output format only needs to be "a
  public MP4 URL," matching what Creatomate already provides today.**

This means Phase 3 does not need to change the two scenarios' eligibility
logic at all once this renderer's output is genuinely 1080×1920 — it only
needs a render step upstream of them that writes `Render_URL` /
`Render_Width` / `Render_Height` / `Render_ID` / `Render_Requested_At` onto
the matching data store record, the same shape Creatomate's step already
writes today.

## Target shape: synchronous HTTP job per the brief

```
POST /render
Body: the video spec JSON (same shape as samples/sample_spec.json)

Response 200:
{
  "job_id": "…",
  "status": "completed" | "failed",
  "video_url": "https://…/<job_id>.mp4",   // public or signed
  "width": 1080,
  "height": 1920,
  "duration": 11.6,
  "error": null | { "message": "…", "stage": "render" | "verify" | "asset" }
}
```

This is a thin HTTP wrapper around `renderer.runner.run_job` (already
built): receive the spec, call `run_job`, upload the resulting file to
wherever "public or signed URL" means for this account (Backblaze B2 — the
account already has a `creatomate-c8xg3hsxdu` bucket conventions suggest
— or Cloudinary, which `Asset_Screenshot_URL` values already use), and
return the JSON above. A Make **HTTP** module (`http:ActionMakeRequest`,
the same package already used in scenario 6793516) can call this directly;
no new Make app/connection type is needed beyond the generic HTTP module
already in use.

Make-side wiring (for a human to do later, not this change):
1. New scenario step, upstream of both publish scenarios: `datastore:SearchRecord`
   for `Status=READY, Render_URL=empty` (or whatever marks "needs render") →
   `http:ActionMakeRequest` to `POST /render` with the spec built from that
   record's `Hook`/`Caption`/`CTA`/`Script`/asset fields → `datastore:UpdateRecord`
   writing `Render_URL`, `Render_Width=1080`, `Render_Height=1920`,
   `Render_ID={{job_id}}`, `Render_Requested_At={{now}}`, and `Error_Note`
   on failure (mirroring the existing `PUBLISH_FAILED`/`UPLOAD_FAILED` pattern
   already in both scenarios).
2. No changes needed inside 6793356 or 6793516 themselves — they already key
   off `Render_URL`/`Render_Width`/`Render_Height` exactly as this renderer
   would populate them.

## Where should this run: local worker, cloud worker, or VPS?

| Option | Recurring cost | Ops burden | Verdict |
|---|---|---|---|
| **Local worker** (this machine, Make HTTP calls `localhost`/a tunnel) | $0 | Must stay powered on and reachable; a tunnel (ngrok/Cloudflare Tunnel, free tiers exist) is a single point of failure and an extra moving part | Fine for **testing**, not for a scheduled production pipeline — Make scenarios run on Make's schedule, not yours, so the renderer must be reachable 24/7 |
| **Small VPS** (e.g. a $4–6/mo 1-2 vCPU box — Hetzner CX22, DigitalOcean/Vultr equivalent) | ~$5–7/mo | You own OS updates, ffmpeg/font updates, disk space for temp renders, process supervision (systemd unit around `shorts-render`), basic monitoring | **Recommended for Phase 3** — cheapest option that's actually always-on and reachable by Make without a tunnel; matches the "low-cost" brief directly |
| **Cloud worker (serverless / managed container)** (e.g. a scheduled container job, or a small always-on container service) | Highly variable — roughly $0–15/mo at this volume (a handful of ≤30s renders/day), but FFmpeg + font install inside a container image adds build/registry complexity, and cold starts hurt a synchronous HTTP contract | Worth it **only** once render volume or concurrency grows enough that a single VPS becomes the bottleneck, or once availability requirements go beyond what a lone VPS reasonably gives | Overkill today for ~11 records/handful of renders a day |

**Recommendation: a small VPS**, running `shorts-render` behind a tiny HTTP
wrapper (a single `/render` endpoint, e.g. `http.server` + a worker pool, or
a one-file `uvicorn`/stdlib `http.server` app — intentionally not building
this yet per "do not overbuild it in the first implementation") under
`systemd`, with the VPS's own reverse-proxy TLS (Caddy auto-TLS is free) so
Make's HTTP module can call `https://render.yourdomain/render` directly. No
paid service beyond the VPS itself (~$5–7/mo) is required; this is why the
schema and CLI have zero third-party dependencies — the same code that runs
in this review environment is what would run on that VPS.

## Operational requirements on that VPS

- `ffmpeg` + `ffprobe` (apt), `fonts-noto-cjk` (apt) — both already proven
  to work in this exact form in this change.
- Enough disk for temporary render work-dirs (cleaned up automatically by
  `runner.run_job`'s `finally` block) — a few hundred MB headroom is ample
  at current output sizes (~600KB for an 11.6s clip at the settings used
  here; real cinematic footage will be larger, budget for low hundreds of
  MB per concurrent render).
- A systemd unit (`Restart=on-failure`) around the HTTP wrapper so a crashed
  worker process comes back without manual intervention.
- Upload target for the rendered MP4 (`video_url` in the response) — reuse
  whatever bucket/CDN already serves `Render_URL` values today (Backblaze
  B2, going by the existing Creatomate URLs) rather than introducing a new
  storage provider.
- Basic log shipping: `runner.py` already emits structured JSON lines to
  stderr; redirecting the systemd unit's stderr to a file (or `journald`,
  which is already structured) is enough at this scale — no paid logging
  service needed.

## Explicitly out of scope for Phase 3 (per the brief)

- No Make scenario, connection, or data store schema was modified.
- No publish to Instagram or YouTube was triggered or tested.
- No paid service (upscaling API, TTS API, cloud render farm) was added or
  assumed — the VPS recommendation above is the only recurring cost, and it
  requires explicit approval before anyone provisions it.
