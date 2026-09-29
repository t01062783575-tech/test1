# EpicCut Studio — Staged Implementation Plan

Gate rule (per spec): do not start phase N+1 until phase N's tests pass.

## Phase A — CLI + FFmpeg engine + recipe schema + tests  ✅ this change

1. Recipe JSON schema (versioned, dataclass-based, `to_dict`/`from_dict`).
2. Validation module with a typed `RecipeError`.
3. `ffprobe` wrapper → `MediaInfo`.
4. Retiming math (constant-speed case; 5.04s→12s is the canonical test).
5. Audio plan (trim/offset/fade/volume) as pure filter-graph data.
6. Command builder: recipe + MediaInfo → concrete `ffmpeg` argv list.
7. Runner: subprocess execution, cancellation, temp cleanup.
8. QA: `ffprobe`-based post-export verification.
9. Adapters: RIFE / Real-ESRGAN detection stubs that never crash the base
   editor when absent.
10. CLI: `epiccut render recipe.json`, `epiccut surreal ...`.
11. Tests per FEATURE_MATRIX.md. **Gate: all Phase A tests pass before Phase B.**

## Phase B — Epic Surreal Auto Finish

1. Wire probe → retiming → (optional stabilize) → (optional flicker
   reduction) → motion-aware retiming → (optional RIFE) → camera-motion →
   grade → (optional bloom/vignette/grain) → music extraction → normalize →
   fades → 1080x1920 render → QA, as one pipeline function with per-step
   toggles.
2. Visual enhancement + effects filters (exposure/contrast/highlights/
   shadows/saturation/temperature/tint/gamma/sharpen/denoise; vignette/bloom/
   grain/haze/LUT), all bypassable.
3. Sacred Temple / Cosmic Monument / Liminal Cathedral / Dream Landscape
   presets as concrete filter graphs (Phase A only defines their data).
4. Flicker reduction pass (conservative, exposure-fluctuation targeted).
5. Auto Reframe v1 (manual focal point, center crop, safe zones) for the four
   aspect presets.
6. Audio EQ/compressor/limiter/ducking; beat analysis + "align climax to end".
7. Still-image Ken Burns mode.
8. Provider-watermark detection warning (no auto-crop-to-hide).
9. Tests: full 15-step Auto Finish on a generated sample; each optional step
   toggled off individually still produces valid output.

## Phase C — PySide6 GUI

1. Timeline widget bound to the recipe (multi-track video/audio/overlay).
2. Trim/split/delete/reorder/crop/transform via direct manipulation → recipe
   mutations → same render path as CLI.
3. Keyframe editor (position/scale/rotation/opacity/volume; 4 interpolation
   curves) evaluated into per-frame filter expressions for preview + export.
4. Proxy preview (360p/540p) with caching; final-quality render on export.
5. Undo/redo over recipe mutations.
6. Batch queue (pending/processing/completed/failed) that doesn't stop on one
   failure.

## Phase D — RIFE / Real-ESRGAN real adapters

1. Real `interpolate()` / `upscale()` bodies behind the Phase A adapter
   interfaces (installation detection already exists).
2. Interpolation-strength / target-FPS config, progress reporting, output
   caching, safe temp-frame cleanup.
3. Real-ESRGAN 1.5x/2x/4x, FFmpeg lanczos fallback when unavailable (fallback
   itself is trivial and can land opportunistically in B, but the adapter
   integration point is gated here).

## Phase E — Short-form speech/caption tools

1. Whisper transcription (optional, off by default for Epic Surreal projects).
2. Auto captions, styles, safe zones.
3. Silence detection/removal, filler-word markers.
4. Scene detection, highlight markers.

## Explicit non-goals (per spec, do not implement)

- Social publishing.
- Watermark removal (detection + warning only).
- Automatic cropping specifically to hide a provider mark.
