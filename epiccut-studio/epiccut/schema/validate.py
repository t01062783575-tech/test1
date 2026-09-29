"""Semantic validation for a parsed Recipe.

`Recipe.from_dict` already rejects structurally malformed JSON (missing
required keys, unknown enum values). `validate_recipe` catches everything
that is well-formed but semantically nonsensical: dangling references,
negative durations, out-of-range values, etc. Both layers raise
`RecipeError` so callers only need to catch one exception type.
"""

from __future__ import annotations

from epiccut.errors import RecipeError
from epiccut.schema.recipe import Recipe


def validate_recipe(recipe: Recipe) -> None:
    issues: list[str] = []

    media_ids = set(recipe.media.keys())
    track_ids = {t.id for t in recipe.tracks}
    all_clip_ids: set[str] = set()

    if len(track_ids) != len(recipe.tracks):
        issues.append("duplicate track ids in 'tracks'")

    for track in recipe.tracks:
        for clip in track.clips:
            if clip.id in all_clip_ids:
                issues.append(f"duplicate clip id '{clip.id}'")
            all_clip_ids.add(clip.id)

            if clip.track_id != track.id:
                issues.append(
                    f"clip '{clip.id}' has track_id '{clip.track_id}' but is listed under track '{track.id}'"
                )

            if clip.media_id not in media_ids:
                issues.append(f"clip '{clip.id}' references unknown media_id '{clip.media_id}'")

            if clip.source_in < 0:
                issues.append(f"clip '{clip.id}' has negative source_in ({clip.source_in})")

            if clip.source_out is not None and clip.source_out <= clip.source_in:
                issues.append(
                    f"clip '{clip.id}' has source_out ({clip.source_out}) <= source_in ({clip.source_in})"
                )

            if clip.timeline_start < 0:
                issues.append(f"clip '{clip.id}' has negative timeline_start ({clip.timeline_start})")

            speed = clip.speed
            if speed.mode == "constant" and speed.factor <= 0:
                issues.append(f"clip '{clip.id}' has non-positive constant speed factor ({speed.factor})")
            if speed.mode == "target_duration" and (speed.target_duration is None or speed.target_duration <= 0):
                issues.append(f"clip '{clip.id}' speed mode 'target_duration' requires a positive target_duration")

            if clip.fade.fade_in < 0 or clip.fade.fade_out < 0:
                issues.append(f"clip '{clip.id}' has a negative fade duration")

    for transition in recipe.transitions:
        if transition.clip_a_id not in all_clip_ids:
            issues.append(f"transition references unknown clip_a_id '{transition.clip_a_id}'")
        if transition.clip_b_id not in all_clip_ids:
            issues.append(f"transition references unknown clip_b_id '{transition.clip_b_id}'")
        if transition.duration < 0:
            issues.append("transition has a negative duration")

    if recipe.audio is not None:
        audio = recipe.audio
        if audio.source_media_id is not None and audio.source_media_id not in media_ids:
            issues.append(f"audio references unknown source_media_id '{audio.source_media_id}'")
        if audio.start < 0:
            issues.append(f"audio.start is negative ({audio.start})")
        if audio.duration is not None and audio.duration <= 0:
            issues.append(f"audio.duration must be positive if set (got {audio.duration})")
        if audio.fade_in < 0 or audio.fade_out < 0:
            issues.append("audio has a negative fade duration")
        if not (0.0 <= audio.volume <= 4.0):
            issues.append(f"audio.volume {audio.volume} is out of the supported 0.0-4.0 range")

    export = recipe.export
    if export.width <= 0 or export.height <= 0:
        issues.append(f"export dimensions must be positive (got {export.width}x{export.height})")
    if export.fps <= 0:
        issues.append(f"export.fps must be positive (got {export.fps})")
    if export.crf is not None and not (0 <= export.crf <= 51):
        issues.append(f"export.crf {export.crf} is outside the valid 0-51 range")

    reframe = recipe.reframe
    if not (0.0 <= reframe.focal_point[0] <= 1.0 and 0.0 <= reframe.focal_point[1] <= 1.0):
        issues.append(f"reframe.focal_point {reframe.focal_point} must be within [0,1] x [0,1]")

    if issues:
        raise RecipeError("; ".join(issues))
