import pytest

from epiccut.engine.retiming import compute_retiming, output_fps_for_retiming, setpts_filter


def test_5_04s_to_12s_retiming_is_a_single_continuous_stretch():
    """The canonical spec case: a 5.04s clip must become a continuous 12s
    output without repeating or concatenating the clip — i.e. exactly one
    speed factor, not a loop count."""
    plan = compute_retiming(5.04, 12.0)

    assert plan.speed_factor == pytest.approx(12.0 / 5.04)
    assert plan.speed_factor == pytest.approx(2.380952, rel=1e-4)
    assert plan.playback_rate == pytest.approx(5.04 / 12.0)

    # This is the "no repeat/concat" guarantee: source_duration * speed_factor
    # must land exactly on target_duration for a single setpts stretch.
    assert plan.source_duration * plan.speed_factor == pytest.approx(12.0)


def test_extreme_slowdown_flags_judder_risk_and_recommends_rife():
    plan = compute_retiming(5.04, 12.0)
    assert plan.judder_risk is True
    assert plan.recommend_rife is True


def test_judder_risk_suppressed_when_interpolation_already_allowed():
    plan = compute_retiming(5.04, 12.0, allow_interpolation=True)
    assert plan.judder_risk is True
    assert plan.recommend_rife is False  # already handled, no need to recommend


def test_mild_retiming_does_not_flag_judder_risk():
    plan = compute_retiming(10.0, 11.0)  # 1.1x change, well under threshold
    assert plan.judder_risk is False
    assert plan.recommend_rife is False


def test_speedup_case_is_symmetric():
    plan = compute_retiming(12.0, 5.04)
    assert plan.speed_factor == pytest.approx(5.04 / 12.0)
    assert plan.judder_risk is True  # same ratio, opposite direction


@pytest.mark.parametrize("source,target", [(0.0, 12.0), (-1.0, 12.0), (5.04, 0.0), (5.04, -1.0)])
def test_invalid_durations_raise(source, target):
    with pytest.raises(ValueError):
        compute_retiming(source, target)


def test_setpts_filter_expression():
    assert setpts_filter(2.0) == "setpts=2.0000000000*PTS"


def test_setpts_filter_rejects_non_positive_factor():
    with pytest.raises(ValueError):
        setpts_filter(0.0)


def test_output_fps_defaults_to_source_fps():
    assert output_fps_for_retiming(24.0, speed_factor=2.38) == 24.0


def test_output_fps_honors_explicit_target():
    assert output_fps_for_retiming(24.0, speed_factor=2.38, target_fps=60.0) == 60.0
