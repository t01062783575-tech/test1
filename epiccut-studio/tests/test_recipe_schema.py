import json

import pytest

from epiccut.errors import RecipeError
from epiccut.schema.recipe import (
    Clip,
    Keyframe,
    KeyframedProperty,
    MediaRef,
    Recipe,
    SpeedCurve,
    Track,
    Transform,
)
from epiccut.schema.validate import validate_recipe


def _minimal_recipe() -> Recipe:
    media = {"video": MediaRef(id="video", path="/tmp/source.mp4", kind="video")}
    clip = Clip(id="c0", media_id="video", track_id="v0")
    track = Track(id="v0", kind="video", clips=[clip])
    return Recipe(media=media, tracks=[track])


def test_round_trip_minimal_recipe():
    recipe = _minimal_recipe()
    d = recipe.to_dict()
    json_text = json.dumps(d, ensure_ascii=False)  # must be JSON-serializable
    restored = Recipe.from_dict(json.loads(json_text))
    assert restored.to_dict() == d


def test_round_trip_with_keyframes():
    position_kf = KeyframedProperty(keyframes=[
        Keyframe(time=0.0, value=[0.0, 0.0], interpolation="ease_in"),
        Keyframe(time=1.0, value=[100.0, -50.0], interpolation="ease_out"),
        Keyframe(time=2.0, value=[0.0, 0.0], interpolation="linear"),
    ])
    opacity_kf = KeyframedProperty(keyframes=[
        Keyframe(time=0.0, value=0.0, interpolation="ease_in_out"),
        Keyframe(time=0.5, value=1.0, interpolation="ease_in_out"),
    ])
    transform = Transform(position=position_kf, opacity=opacity_kf)
    clip = Clip(id="c0", media_id="video", track_id="v0", transform=transform)
    recipe = Recipe(
        media={"video": MediaRef(id="video", path="/tmp/a.mp4", kind="video")},
        tracks=[Track(id="v0", kind="video", clips=[clip])],
    )

    d = recipe.to_dict()
    restored = Recipe.from_dict(json.loads(json.dumps(d)))

    restored_clip = restored.tracks[0].clips[0]
    assert restored_clip.transform.position.is_keyframed()
    assert len(restored_clip.transform.position.keyframes) == 3
    assert restored_clip.transform.position.keyframes[1].value == [100.0, -50.0]
    assert restored_clip.transform.position.keyframes[1].interpolation == "ease_out"
    assert restored_clip.transform.opacity.keyframes[1].value == 1.0


def test_speed_curve_target_duration_round_trip():
    clip = Clip(
        id="c0", media_id="video", track_id="v0",
        speed=SpeedCurve(mode="target_duration", target_duration=12.0, allow_interpolation=True),
    )
    recipe = Recipe(
        media={"video": MediaRef(id="video", path="/tmp/a.mp4", kind="video")},
        tracks=[Track(id="v0", kind="video", clips=[clip])],
    )
    restored = Recipe.from_dict(json.loads(json.dumps(recipe.to_dict())))
    speed = restored.tracks[0].clips[0].speed
    assert speed.mode == "target_duration"
    assert speed.target_duration == 12.0
    assert speed.allow_interpolation is True


def test_missing_audio_is_valid_and_serializes_as_none():
    recipe = _minimal_recipe()
    assert recipe.audio is None
    d = recipe.to_dict()
    assert d["audio"] is None
    restored = Recipe.from_dict(d)
    assert restored.audio is None
    validate_recipe(restored)  # should not raise


def test_incompatible_schema_major_version_rejected():
    d = _minimal_recipe().to_dict()
    d["schema_version"] = "99.0.0"
    with pytest.raises(RecipeError):
        Recipe.from_dict(d)


@pytest.mark.parametrize("mutation, expected_message_fragment", [
    (lambda d: d["tracks"][0]["clips"][0].update(media_id="does-not-exist"), "unknown media_id"),
    (lambda d: d["tracks"][0]["clips"][0].update(source_in=-1.0), "negative source_in"),
    (lambda d: d["tracks"][0]["clips"][0].update(source_in=5.0, source_out=2.0), "source_out"),
    (lambda d: d["tracks"][0]["clips"][0].update(speed={"mode": "constant", "factor": 0.0}), "speed factor"),
])
def test_semantically_invalid_recipes_are_rejected(mutation, expected_message_fragment):
    d = _minimal_recipe().to_dict()
    mutation(d)
    recipe = Recipe.from_dict(d)
    with pytest.raises(RecipeError, match=expected_message_fragment):
        validate_recipe(recipe)


def test_structurally_invalid_json_is_rejected():
    with pytest.raises(RecipeError):
        Recipe.from_dict({"tracks": [{"id": "v0", "kind": "not-a-real-kind"}]})


def test_clip_track_id_mismatch_is_rejected():
    d = _minimal_recipe().to_dict()
    d["tracks"][0]["clips"][0]["track_id"] = "some-other-track"
    recipe = Recipe.from_dict(d)
    with pytest.raises(RecipeError, match="track_id"):
        validate_recipe(recipe)


def test_export_dimension_validation():
    recipe = _minimal_recipe()
    recipe.export.width = 0
    with pytest.raises(RecipeError, match="dimensions"):
        validate_recipe(recipe)
