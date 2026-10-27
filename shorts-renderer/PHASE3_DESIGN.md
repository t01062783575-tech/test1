# Phase 3 — Make.com Integration

**Status: the HTTP rendering API is implemented and proven locally
(`renderer/api/`). The Make.com side — the scenario wiring described
below — is still a design only, per the brief ("Do not modify Make yet").**
Nothing in this document has been applied to any live Make scenario,
connection, or data store record — the two scenarios and the data store
described below were inspected read-only (Make MCP) to ground this design
in the real pipeline; that inspection was not repeated in the HTTP-API
change below since the connection was unavailable that session, so the
field contract below reflects the state as of the read in `PHASE3_DESIGN.md`'s
original write-up — reconfirm before wiring Make if the scenarios have
changed since.

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

## Implemented: the HTTP rendering API (`renderer/api/`)

Async, not synchronous (a render can take longer than Make's HTTP module
default timeout, and async lets Make poll rather than hold a connection
open) — job-queue shape, per this change's brief:

```
POST   /render                    Bearer auth   -> 202 {job_id, status: "queued", created: true}
                                                     (or 200 {..., created: false} if job_id already exists — idempotent, no duplicate render)
GET    /jobs/{job_id}             Bearer auth   -> {job_id, status, width, height, duration, error, created_at, updated_at}
GET    /jobs/{job_id}/signed-url  Bearer auth   -> {url, expires_at}   (only once status == "completed")
GET    /jobs/{job_id}/output      Bearer auth OR valid ?exp=&sig=   -> the MP4 bytes
GET    /healthz                   no auth        -> {"status": "ok"}
```

Proven end to end with a real running server + `curl` (not just pytest):
`POST /render` → polled `queued` → `processing` → `completed` → minted a
signed URL → downloaded the MP4 **with no Authorization header** (same as
Make's `http:DownloadFile` with `authenticationType: noAuth`, which is
exactly how scenario 6793516 already downloads `Render_URL` today) →
independently re-verified with a fresh `ffprobe` call: 1080×1920, h264/
yuv420p, aac 48000Hz, 5.1s, nonzero bitrate. Re-POSTing the same `job_id`
returned `HTTP 200 {"created": false}` — confirmed no second render ran.

Auth: `Authorization: Bearer <SHORTS_RENDERER_API_KEY>` on every route
except `/healthz` and a validly-signed `/output` link. The server refuses
to start at all if `SHORTS_RENDERER_API_KEY` isn't set (`AuthNotConfigured`)
— there is no mode where `/render` runs unauthenticated.

Start it: `shorts-render serve --port 8080 --db jobs.sqlite3 --output-dir render_output --concurrency 2`
(see `README.md` for the full option list). Job state lives in sqlite
(`--db`), survives a server restart, and tracks `queued → processing →
completed|failed` with timestamps.

## Make-side wiring (design only — not applied to Make in this change)

1. New scenario step, upstream of both publish scenarios: `datastore:SearchRecord`
   for `Status=READY, Render_URL=empty` (or whatever marks "needs render").
2. `http:ActionMakeRequest` → `POST {base_url}/render`, header
   `Authorization: Bearer {{connection secret}}`, JSON body built from that
   record's `Hook`/`Caption`/`CTA`/`Script`/asset fields into this renderer's
   spec shape (`samples/sample_spec.json`), with `"job_id": "{{1.Render_ID}}"`
   (or the record key) so a Make replay/retry is automatically idempotent
   against this API rather than triggering a second render.
3. A **sleep/repeat loop** (Make's built-in `Sleep` + router-back-to-self, or
   a scheduled "poll" scenario) calling `GET {base_url}/jobs/{{job_id}}`
   every N seconds until `status` is `completed` or `failed` — mirrors how
   Make already polls/re-triggers on its own schedule elsewhere in this
   account.
4. On `completed`: `GET {base_url}/jobs/{{job_id}}/signed-url` (Bearer auth)
   → `datastore:UpdateRecord` writing `Render_URL = {{url}}`,
   `Render_Width=1080`, `Render_Height=1920`, `Render_ID={{job_id}}`,
   `Render_Requested_At={{now}}`. From here 6793356/6793516 need **zero
   changes** — they already key off exactly these fields.
5. On `failed`: `datastore:UpdateRecord` writing `Error_Note = {{error}}`,
   mirroring the existing `PUBLISH_FAILED`/`UPLOAD_FAILED` pattern already
   in both scenarios. Do not auto-retry the render from Make's side beyond
   its own built-in error-handler retry count — re-running this *scenario*
   is safe (idempotent on `job_id`), but nothing here should auto-generate
   a **new** `job_id` for a record that already failed without a human
   deciding to re-queue it, per "never render or publish duplicates
   automatically."

The `Authorization` Bearer value belongs in a Make **connection**
(credential store), never typed into a module's visible parameters or a
data store field — this keeps the API key out of scenario blueprints and
execution logs, mirroring how the existing Instagram/YouTube connections
already keep their tokens out of the visible mapper.

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

## Exact remaining steps to connect Make (none completed yet)

1. **Decide hosting and get it reachable from Make's cloud, not just
   localhost.** This sandbox proved the API works via local `curl`; Make's
   servers cannot reach a container in this session. Two options, neither
   taken yet because both cost money or expose a port — **your call**:
   - Safest temporary option for a one-off connectivity test: a free
     `cloudflared tunnel --url http://localhost:8080` (no account needed for
     a quick `trycloudflare.com` URL, auto-HTTPS, link expires when the
     tunnel process ends) — exposes this one port only, for as long as you
     choose to run it, nothing persistent.
   - Production option: the VPS described above (~$5-7/mo, requires your
     approval before provisioning).
2. **Set real secrets** on whichever host runs it: `SHORTS_RENDERER_API_KEY`
   (long random value) and optionally `SHORTS_RENDERER_SIGNING_SECRET`
   (defaults to the API key if unset). Put the same API key value into a
   Make connection (not a visible module field).
3. **Build and test the upstream "needs render" scenario** (step 1-5 above)
   against a `TEST`/`TEST_READY` record first, the same safe pattern the
   existing YouTube scenario already uses, before pointing it at real
   `READY`+`Approval=YES` records.
4. **Verify 6793356/6793516 still require no changes** once a real record
   has `Render_Width=1080`/`Render_Height=1920` from this renderer — expected
   to just work per the field contract above, but worth confirming with one
   real (TEST-flagged, non-publishing) run through to `YT_Status=UPLOADED_PRIVATE`
   the way `PIPE-TEST-001` already proved the rest of the pipeline once.

## Explicitly out of scope for Phase 3 (per the brief)

- No Make scenario, connection, or data store schema was modified.
- No publish to Instagram or YouTube was triggered or tested.
- No paid service (upscaling API, TTS API, cloud render farm, VPS, tunnel)
  was added, provisioned, or assumed — the HTTP API was proven entirely
  against `localhost` inside this session; nothing was exposed to the
  public internet.
