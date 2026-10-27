"""Real ffmpeg renders + ffprobe verification — these are the tests that
actually exercise the renderer end to end, not just its Python logic."""

import os

import pytest

from renderer.probe import probe
from renderer.runner import run_job
from renderer.schema import VideoSpec
from tests.conftest import requires_ffmpeg


def _two_scene_spec(assets: dict, job_id: str = "test-job") -> dict:
    return {
        "job_id": job_id,
        "output": {"width": 1080, "height": 1920, "fps": 30},
        "safe_zones": {"top": 150, "bottom": 220},
        "fade_in": 0.3,
        "fade_out": 0.5,
        "voiceover": {"source": assets["voice"], "volume": 1.0},
        "background_music": {"source": assets["music"], "volume": 0.15, "fade_in": 0.5, "fade_out": 1.0},
        "scenes": [
            {
                "id": "scene_1",
                "duration": 4.0,
                "background": {"source": assets["bg1"], "kind": "image", "fit": "cover"},
                "texts": [
                    {"content": "AI 도구 추천 TOP 3", "position": "top", "font_size": 72, "start": 0.2, "end": 3.8, "animation": "fade"},
                ],
                "subtitles": [
                    {"text": "오늘은 AI 도구 세 가지를 소개합니다.", "start": 0.3, "end": 3.7},
                ],
            },
            {
                "id": "scene_2",
                "duration": 3.0,
                "background": {"source": assets["bg2"], "kind": "image", "fit": "cover"},
                "transition_in": {"type": "fade", "duration": 0.5},
                "texts": [
                    {"content": "Save this for later", "position": "bottom", "font_size": 60, "start": 0.0, "end": 2.5, "animation": "slide_up"},
                ],
                "subtitles": [
                    {"text": "저장해두고 필요할 때 다시 보세요.", "start": 0.0, "end": 2.8},
                ],
            },
        ],
    }


@requires_ffmpeg
def test_milestone_two_scene_render_with_subtitles_and_synced_audio(tmp_path, two_scene_spec_paths):
    """The requested first milestone: >=2 scenes, readable subtitles,
    synchronized audio, real 1080x1920 output, verified with ffprobe."""
    spec_dict = _two_scene_spec(two_scene_spec_paths)
    spec = VideoSpec.from_dict(spec_dict)
    output_path = str(tmp_path / "milestone.mp4")

    result = run_job(spec, output_path, timeout=120)

    assert result.status == "completed", result.error
    assert result.job_id == "test-job"
    assert result.width == 1080
    assert result.height == 1920
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0

    info = probe(output_path)
    assert info.width == 1080 and info.height == 1920
    assert info.video_codec == "h264"
    assert info.has_audio is True
    assert info.audio_codec == "aac"
    assert info.audio_sample_rate == 48000
    # 4.0 + 3.0 - 0.5s crossfade overlap
    assert abs(info.duration - 6.5) < 0.15
    assert abs((info.audio_duration or 0) - info.duration) < 0.2


@requires_ffmpeg
def test_render_without_audio_has_no_audio_stream(tmp_path, two_scene_spec_paths):
    spec = VideoSpec.from_dict({
        "scenes": [{"duration": 2.0, "background": {"source": two_scene_spec_paths["bg1"]}}],
    })
    output_path = str(tmp_path / "silent.mp4")
    result = run_job(spec, output_path, timeout=60)

    assert result.status == "completed", result.error
    info = probe(output_path)
    assert info.has_audio is False


@requires_ffmpeg
def test_unique_job_ids_when_not_specified(tmp_path, two_scene_spec_paths):
    spec_a = VideoSpec.from_dict({"scenes": [{"duration": 1.0, "background": {"source": two_scene_spec_paths["bg1"]}}]})
    spec_b = VideoSpec.from_dict({"scenes": [{"duration": 1.0, "background": {"source": two_scene_spec_paths["bg1"]}}]})
    assert spec_a.job_id != spec_b.job_id


@requires_ffmpeg
def test_missing_background_asset_reports_failed_job_not_a_crash(tmp_path):
    spec = VideoSpec.from_dict({
        "scenes": [{"duration": 2.0, "background": {"source": str(tmp_path / "does_not_exist.png")}}],
    })
    result = run_job(spec, str(tmp_path / "out.mp4"), timeout=30)

    assert result.status == "failed"
    assert "not found" in result.error
    assert not os.path.exists(tmp_path / "out.mp4")


@requires_ffmpeg
def test_render_timeout_is_enforced_and_cleans_up_partial_output(tmp_path, two_scene_spec_paths):
    # A deliberately slow encode (high CRF range irrelevant; use a long
    # scene + slow preset indirectly by requesting many scenes would be
    # complex to set up — instead verify the timeout *mechanism* directly
    # with an unreasonably small timeout against a real multi-second job.
    spec = VideoSpec.from_dict({
        "scenes": [
            {"duration": 6.0, "background": {"source": two_scene_spec_paths["bg1"]}},
            {"duration": 6.0, "background": {"source": two_scene_spec_paths["bg2"]},
             "transition_in": {"type": "dissolve", "duration": 1.0}},
        ],
    })
    output_path = str(tmp_path / "timeout.mp4")
    result = run_job(spec, output_path, timeout=0.01)

    assert result.status == "failed"
    assert "timeout" in result.error.lower() or "timed out" in result.error.lower()
    assert not os.path.exists(output_path)


@requires_ffmpeg
def test_verification_catches_a_mismatched_expectation(tmp_path, two_scene_spec_paths):
    """verify() must actually fail closed: if we ask it to check for a
    duration the real file doesn't have, it should say so."""
    from renderer.probe import verify

    spec = VideoSpec.from_dict({"scenes": [{"duration": 2.0, "background": {"source": two_scene_spec_paths["bg1"]}}]})
    output_path = str(tmp_path / "out.mp4")
    result = run_job(spec, output_path, timeout=60, verify_output=False)
    assert result.status == "completed"

    ok, issues, info = verify(
        output_path, expected_duration=99.0, expected_width=1080, expected_height=1920,
        expected_fps=30, expected_video_codec="h264", expect_audio=False,
    )
    assert ok is False
    assert any("duration" in issue for issue in issues)


def test_invalid_spec_json_is_rejected_by_cli(tmp_path):
    from renderer.cli import main

    bad_spec = tmp_path / "bad.json"
    bad_spec.write_text('{"scenes": []}', encoding="utf-8")
    rc = main(["render", str(bad_spec), "--output", str(tmp_path / "out.mp4")])
    assert rc == 1


def test_nonexistent_spec_file_is_rejected_by_cli(tmp_path):
    from renderer.cli import main

    rc = main(["render", str(tmp_path / "nope.json")])
    assert rc == 1
