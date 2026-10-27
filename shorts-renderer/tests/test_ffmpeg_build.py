from renderer.ffmpeg_build import build_render_command
from renderer.schema import VideoSpec


def _dummy_image(tmp_path, name="bg.png"):
    path = tmp_path / name
    path.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "53de0000000c4944415408d763f8ffff3f0005fe02fea739666500000000"
        "49454e44ae426082"
    ))
    return str(path)


def test_single_scene_command_structure(tmp_path):
    spec = VideoSpec.from_dict({"scenes": [{"duration": 3.0, "background": {"source": _dummy_image(tmp_path)}}]})
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))

    assert built.argv[0].endswith("ffmpeg")
    assert built.argv.count("-i") == 1
    assert "-filter_complex" in built.argv
    assert "-map" in built.argv
    assert built.expected_duration == 3.0
    assert built.expects_audio is False
    assert "[aout]" not in " ".join(built.argv)  # no audio map when none requested


def test_two_scenes_without_transition_use_concat(tmp_path):
    spec = VideoSpec.from_dict({
        "scenes": [
            {"duration": 3.0, "background": {"source": _dummy_image(tmp_path, "a.png")}},
            {"duration": 2.0, "background": {"source": _dummy_image(tmp_path, "b.png")}},
        ]
    })
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))
    filter_complex = built.argv[built.argv.index("-filter_complex") + 1]
    assert "concat=n=2" in filter_complex
    assert built.expected_duration == 5.0


def test_two_scenes_with_crossfade_use_xfade_and_shorten_duration(tmp_path):
    spec = VideoSpec.from_dict({
        "scenes": [
            {"duration": 4.0, "background": {"source": _dummy_image(tmp_path, "a.png")}},
            {"duration": 4.0, "background": {"source": _dummy_image(tmp_path, "b.png")},
             "transition_in": {"type": "fade", "duration": 1.0}},
        ]
    })
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))
    filter_complex = built.argv[built.argv.index("-filter_complex") + 1]
    assert "xfade=transition=fade:duration=1.000000" in filter_complex
    assert built.expected_duration == 7.0  # 4 + 4 - 1s overlap


def test_voiceover_only_maps_audio(tmp_path):
    vo = tmp_path / "vo.aac"
    vo.write_bytes(b"not a real aac but resolve_asset only checks existence")
    spec = VideoSpec.from_dict({
        "scenes": [{"duration": 3.0, "background": {"source": _dummy_image(tmp_path)}}],
        "voiceover": {"source": str(vo)},
    })
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))
    assert built.expects_audio is True
    assert "[aout]" in built.argv[built.argv.index("-filter_complex") + 1]
    assert built.argv.count("-i") == 2  # background + voiceover


def test_voiceover_and_music_both_map_and_mix(tmp_path):
    vo = tmp_path / "vo.aac"
    music = tmp_path / "music.aac"
    vo.write_bytes(b"x")
    music.write_bytes(b"x")
    spec = VideoSpec.from_dict({
        "scenes": [{"duration": 3.0, "background": {"source": _dummy_image(tmp_path)}}],
        "voiceover": {"source": str(vo)},
        "background_music": {"source": str(music), "volume": 0.2},
    })
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))
    filter_complex = built.argv[built.argv.index("-filter_complex") + 1]
    assert "amix=inputs=2" in filter_complex
    assert built.argv.count("-i") == 3


def test_cover_fit_uses_crop_then_scale(tmp_path):
    spec = VideoSpec.from_dict({
        "scenes": [{"duration": 3.0, "background": {"source": _dummy_image(tmp_path), "fit": "cover"}}]
    })
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))
    filter_complex = built.argv[built.argv.index("-filter_complex") + 1]
    assert "crop=" in filter_complex
    assert "scale=1080:1920" in filter_complex


def test_contain_fit_uses_scale_then_pad(tmp_path):
    spec = VideoSpec.from_dict({
        "scenes": [{"duration": 3.0, "background": {"source": _dummy_image(tmp_path), "fit": "contain"}}]
    })
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))
    filter_complex = built.argv[built.argv.index("-filter_complex") + 1]
    assert "pad=1080:1920" in filter_complex


def test_video_background_uses_stream_loop(tmp_path):
    bg = tmp_path / "bg.mp4"
    bg.write_bytes(b"x")
    spec = VideoSpec.from_dict({
        "scenes": [{"duration": 5.0, "background": {"source": str(bg), "kind": "video"}}]
    })
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))
    assert "-stream_loop" in built.argv


def test_custom_output_resolution_and_fps_respected(tmp_path):
    spec = VideoSpec.from_dict({
        "output": {"width": 1080, "height": 1920, "fps": 24},
        "scenes": [{"duration": 3.0, "background": {"source": _dummy_image(tmp_path)}}],
    })
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))
    filter_complex = built.argv[built.argv.index("-filter_complex") + 1]
    assert "fps=24" in filter_complex
    r_index = built.argv.index("-r")
    assert built.argv[r_index + 1] == "24"
