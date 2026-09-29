import json

from epiccut.cli import main
from epiccut.engine.qa import QAExpectation, verify_export
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_surreal_5_04s_to_12s_with_music_produces_valid_portrait_export(
    tmp_path, landscape_video_5_04s, music_track_90s
):
    """End-to-end: 5.04s *landscape* AI clip + music -> a continuous 12s
    *portrait* (1080x1920) Reel. Covers retiming, landscape->portrait crop,
    music extraction with an offset, and post-export QA in one real render."""

    output_path = str(tmp_path / "final.mp4")
    recipe_path = str(tmp_path / "recipe.json")

    rc = main([
        "surreal",
        "--video", landscape_video_5_04s,
        "--music", music_track_90s,
        "--duration", "12",
        "--music-start", "10",
        "--music-fade-in", "0.5",
        "--music-fade-out", "1.0",
        "--music-volume", "0.5",
        "--preset", "sacred-temple",
        "--save-recipe", recipe_path,
        "--output", output_path,
    ])

    assert rc == 0

    report = verify_export(
        output_path,
        QAExpectation(duration=12.0, width=1080, height=1920, fps=30, video_codec="h264", expect_audio=True),
    )
    assert report.ok, report.issues

    with open(recipe_path, encoding="utf-8") as f:
        saved_recipe = json.load(f)
    assert saved_recipe["export"]["width"] == 1080
    assert saved_recipe["export"]["height"] == 1920
    assert saved_recipe["audio"]["start"] == 10.0
    assert saved_recipe["enhancement"]["temperature"] == 0.08  # sacred-temple preset applied


@requires_ffmpeg
def test_surreal_without_music_has_no_audio_stream(tmp_path, landscape_video_5_04s):
    output_path = str(tmp_path / "silent.mp4")

    rc = main([
        "surreal",
        "--video", landscape_video_5_04s,
        "--duration", "12",
        "--output", output_path,
    ])

    assert rc == 0
    report = verify_export(
        output_path,
        QAExpectation(duration=12.0, width=1080, height=1920, fps=30, expect_audio=False),
    )
    assert report.ok, report.issues


@requires_ffmpeg
def test_surreal_dry_run_does_not_create_output(tmp_path, landscape_video_5_04s, capsys):
    output_path = str(tmp_path / "never_created.mp4")

    rc = main([
        "surreal",
        "--video", landscape_video_5_04s,
        "--duration", "12",
        "--output", output_path,
        "--dry-run",
    ])

    assert rc == 0
    assert not (tmp_path / "never_created.mp4").exists()
    captured = capsys.readouterr()
    assert "ffmpeg" in captured.out


@requires_ffmpeg
def test_render_missing_recipe_file_reports_clean_error(tmp_path, capsys):
    rc = main(["render", str(tmp_path / "does_not_exist.json")])
    assert rc == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err
