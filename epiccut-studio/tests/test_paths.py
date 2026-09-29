"""Paths containing spaces and Korean characters must survive untouched
through the recipe schema and into the built ffmpeg argv list — no manual
shell-quoting anywhere, since everything is invoked as an argv list."""

from epiccut.engine.command_builder import build_render_command
from epiccut.engine.probe import MediaInfo
from epiccut.schema.recipe import Clip, MediaRef, Recipe, Track

TRICKY_PATH = "/home/user/영상 폴더/내 클립 (최종본).mp4"


def test_tricky_path_round_trips_through_schema():
    media = MediaRef(id="video", path=TRICKY_PATH, kind="video")
    assert media.to_dict()["path"] == TRICKY_PATH
    restored = MediaRef.from_dict(media.to_dict())
    assert restored.path == TRICKY_PATH


def test_tricky_path_appears_verbatim_in_built_argv(tmp_path):
    output_path = str(tmp_path / "출력 파일 (final).mp4")
    media = {"video": MediaRef(id="video", path=TRICKY_PATH, kind="video")}
    clip = Clip(id="c0", media_id="video", track_id="v0")
    recipe = Recipe(media=media, tracks=[Track(id="v0", kind="video", clips=[clip])])
    media_info = {"video": MediaInfo(
        path=TRICKY_PATH, duration=5.04, width=960, height=540, fps=24.0,
        video_codec="h264", has_audio=False, audio_codec=None, audio_duration=None, bit_rate=1_000_000,
    )}

    built = build_render_command(recipe, media_info, output_path)

    # The path must appear as exactly one argv element, unescaped — no
    # quotes or backslashes added, since this never goes through a shell.
    assert TRICKY_PATH in built.argv
    assert output_path in built.argv
    for element in built.argv:
        assert "\\ " not in element  # no manual space-escaping anywhere
        assert not (element.startswith('"') and element.endswith('"'))
