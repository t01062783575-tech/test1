import pytest

from epiccut.engine.audio_plan import plan_music
from epiccut.schema.recipe import AudioSettings


def test_12_second_music_extraction_with_offset():
    """music source: full track, start: 60.0s, duration: 12s — the exact
    example selection given in the spec."""
    audio = AudioSettings(source_media_id="music", start=60.0, duration=12.0, volume=0.30)
    plan = plan_music(audio, source_duration=200.0)

    assert plan.start == 60.0
    assert plan.duration == 12.0
    assert plan.volume == 0.30
    assert "volume=0.300000" in plan.filter_chain()


def test_fade_in_and_fade_out_filters_present():
    audio = AudioSettings(source_media_id="music", start=60.0, duration=12.0, fade_in=0.5, fade_out=1.0)
    plan = plan_music(audio, source_duration=200.0)
    chain = plan.filter_chain()

    assert "afade=t=in:st=0:d=0.500000" in chain
    # fade out should start at duration - fade_out = 11.0s into the extracted segment
    assert "afade=t=out:st=11.000000:d=1.000000" in chain


def test_no_fades_means_no_afade_filters():
    audio = AudioSettings(source_media_id="music", start=0.0, duration=12.0)
    plan = plan_music(audio)
    assert "afade" not in plan.filter_chain()


def test_default_volume_omits_explicit_volume_filter():
    audio = AudioSettings(source_media_id="music", start=0.0, duration=12.0, volume=1.0)
    plan = plan_music(audio)
    assert "volume=" not in plan.filter_chain()


def test_normalize_and_limiter_filters():
    audio = AudioSettings(source_media_id="music", start=0.0, duration=12.0, normalize=True, limiter=True)
    plan = plan_music(audio)
    chain = plan.filter_chain()
    assert "loudnorm" in chain
    assert "alimiter" in chain


@pytest.mark.parametrize("kwargs", [
    dict(start=-1.0, duration=12.0),
    dict(start=0.0, duration=0.0),
    dict(start=0.0, duration=-5.0),
    dict(start=0.0, duration=12.0, fade_in=-0.1),
])
def test_invalid_audio_settings_raise(kwargs):
    audio = AudioSettings(source_media_id="music", **kwargs)
    with pytest.raises(ValueError):
        plan_music(audio)


def test_start_past_known_source_duration_raises():
    audio = AudioSettings(source_media_id="music", start=500.0, duration=12.0)
    with pytest.raises(ValueError):
        plan_music(audio, source_duration=200.0)


def test_start_within_source_duration_but_unknown_duration_is_allowed():
    # source_duration not supplied (e.g. not yet probed) -> no bounds check
    audio = AudioSettings(source_media_id="music", start=500.0, duration=12.0)
    plan_music(audio)  # should not raise
