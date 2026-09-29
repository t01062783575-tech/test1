import subprocess

from epiccut.engine.qa import QAExpectation, verify_export
from tests.conftest import make_test_audio, make_test_video, requires_ffmpeg


@requires_ffmpeg
def test_verify_export_passes_for_a_correct_render(tmp_path):
    path = str(tmp_path / "good.mp4")
    make_test_video(path, duration=3.0, width=1080, height=1920, fps=30)

    report = verify_export(path, QAExpectation(duration=3.0, width=1080, height=1920, fps=30, video_codec="h264", expect_audio=False))
    assert report.ok, report.issues
    assert report.bit_rate and report.bit_rate > 0


@requires_ffmpeg
def test_verify_export_flags_wrong_dimensions(tmp_path):
    path = str(tmp_path / "wrong_dims.mp4")
    make_test_video(path, duration=3.0, width=640, height=360, fps=30)

    report = verify_export(path, QAExpectation(duration=3.0, width=1080, height=1920, fps=30, expect_audio=False))
    assert not report.ok
    assert any("dimensions" in issue for issue in report.issues)


@requires_ffmpeg
def test_verify_export_flags_wrong_duration(tmp_path):
    path = str(tmp_path / "wrong_duration.mp4")
    make_test_video(path, duration=3.0, width=1080, height=1920, fps=30)

    report = verify_export(path, QAExpectation(duration=12.0, width=1080, height=1920, fps=30, expect_audio=False))
    assert not report.ok
    assert any("duration" in issue for issue in report.issues)


@requires_ffmpeg
def test_verify_export_flags_missing_expected_audio(tmp_path):
    path = str(tmp_path / "silent.mp4")
    make_test_video(path, duration=3.0, width=1080, height=1920, fps=30)

    report = verify_export(path, QAExpectation(duration=3.0, width=1080, height=1920, fps=30, expect_audio=True))
    assert not report.ok
    assert any("audio" in issue for issue in report.issues)


def test_verify_export_flags_missing_file(tmp_path):
    report = verify_export(str(tmp_path / "nope.mp4"), QAExpectation(duration=3.0, width=1080, height=1920, fps=30))
    assert not report.ok
    assert any("does not exist" in issue for issue in report.issues)


@requires_ffmpeg
def test_verify_export_flags_zero_byte_file(tmp_path):
    path = tmp_path / "empty.mp4"
    path.write_bytes(b"")
    report = verify_export(str(path), QAExpectation(duration=3.0, width=1080, height=1920, fps=30))
    assert not report.ok
    assert any("empty" in issue or "could not read" in issue for issue in report.issues)


@requires_ffmpeg
def test_verify_export_audio_video_sync_within_tolerance(tmp_path):
    path = str(tmp_path / "with_audio.mp4")
    make_test_video(path, duration=4.0, width=640, height=360, fps=30)
    # Re-mux in a matching-duration audio track so we exercise the has_audio path.
    audio_path = str(tmp_path / "tone.aac")
    make_test_audio(audio_path, duration=4.0)
    muxed = str(tmp_path / "muxed.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", muxed],
        capture_output=True, check=True,
    )

    report = verify_export(muxed, QAExpectation(duration=4.0, width=640, height=360, fps=30, expect_audio=True))
    assert report.ok, report.issues
