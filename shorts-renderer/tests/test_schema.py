import pytest

from renderer.errors import SpecError
from renderer.schema import VideoSpec


def _minimal_spec_dict():
    return {
        "scenes": [
            {"duration": 3.0, "background": {"source": "/tmp/a.png", "kind": "image"}},
        ]
    }


def test_minimal_spec_parses_with_defaults():
    spec = VideoSpec.from_dict(_minimal_spec_dict())
    assert spec.output.width == 1080
    assert spec.output.height == 1920
    assert spec.output.fps == 30
    assert spec.job_id  # auto-generated uuid
    assert len(spec.scenes) == 1


def test_explicit_job_id_is_preserved():
    d = _minimal_spec_dict()
    d["job_id"] = "my-job-123"
    spec = VideoSpec.from_dict(d)
    assert spec.job_id == "my-job-123"


def test_two_scenes_with_crossfade_total_duration():
    d = {
        "scenes": [
            {"duration": 4.0, "background": {"source": "/tmp/a.png"}},
            {"duration": 5.0, "background": {"source": "/tmp/b.png"}, "transition_in": {"type": "fade", "duration": 0.5}},
        ]
    }
    spec = VideoSpec.from_dict(d)
    assert spec.total_duration() == pytest.approx(4.0 + 5.0 - 0.5)


def test_empty_scenes_rejected():
    with pytest.raises(SpecError, match="scenes"):
        VideoSpec.from_dict({"scenes": []})


def test_missing_scenes_key_rejected():
    with pytest.raises(SpecError):
        VideoSpec.from_dict({})


def test_scene_without_background_rejected():
    with pytest.raises(SpecError, match="background"):
        VideoSpec.from_dict({"scenes": [{"duration": 3.0}]})


def test_scene_with_zero_duration_rejected():
    with pytest.raises(SpecError, match="duration"):
        VideoSpec.from_dict({"scenes": [{"duration": 0, "background": {"source": "/tmp/a.png"}}]})


def test_scene_with_negative_duration_rejected():
    with pytest.raises(SpecError, match="duration"):
        VideoSpec.from_dict({"scenes": [{"duration": -2, "background": {"source": "/tmp/a.png"}}]})


def test_unsupported_fps_rejected():
    d = _minimal_spec_dict()
    d["output"] = {"fps": 17}
    with pytest.raises(SpecError, match="fps"):
        VideoSpec.from_dict(d)


def test_unknown_background_kind_rejected():
    d = _minimal_spec_dict()
    d["scenes"][0]["background"]["kind"] = "holodeck"
    with pytest.raises(SpecError, match="background kind"):
        VideoSpec.from_dict(d)


def test_unknown_transition_type_rejected():
    d = _minimal_spec_dict()
    d["scenes"][0]["transition_in"] = {"type": "wipe-diagonal-sparkle"}
    with pytest.raises(SpecError, match="transition"):
        VideoSpec.from_dict(d)


def test_text_overlay_missing_content_rejected():
    d = _minimal_spec_dict()
    d["scenes"][0]["texts"] = [{"position": "top"}]
    with pytest.raises(SpecError, match="content"):
        VideoSpec.from_dict(d)


def test_text_overlay_custom_position_requires_y():
    d = _minimal_spec_dict()
    d["scenes"][0]["texts"] = [{"content": "hi", "position": "custom"}]
    with pytest.raises(SpecError, match="'y'"):
        VideoSpec.from_dict(d)


def test_subtitle_end_before_start_rejected():
    d = _minimal_spec_dict()
    d["scenes"][0]["subtitles"] = [{"text": "hi", "start": 2.0, "end": 1.0}]
    with pytest.raises(SpecError, match="end"):
        VideoSpec.from_dict(d)


def test_voiceover_and_music_round_trip():
    d = _minimal_spec_dict()
    d["voiceover"] = {"source": "/tmp/vo.mp3", "volume": 0.9}
    d["background_music"] = {"source": "/tmp/music.mp3", "volume": 0.2, "fade_in": 0.5, "fade_out": 1.0}
    spec = VideoSpec.from_dict(d)
    assert spec.voiceover.volume == 0.9
    assert spec.background_music.fade_out == 1.0


def test_missing_voiceover_and_music_is_valid():
    spec = VideoSpec.from_dict(_minimal_spec_dict())
    assert spec.voiceover is None
    assert spec.background_music is None


def test_non_dict_spec_rejected():
    with pytest.raises(SpecError):
        VideoSpec.from_dict("not a dict")  # type: ignore[arg-type]
