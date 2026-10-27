"""No shell command injection, no filter-string breakage: malicious or
just-awkward user text (quotes, colons, backticks, `$(...)`, semicolons,
Korean, newlines) must never appear directly inside an ffmpeg argv element
or filter-graph string — only inside a text file we control."""

import os

from renderer.ffmpeg_build import build_render_command
from renderer.schema import VideoSpec
from renderer.textutil import write_text_file

MALICIOUS_SNIPPETS = [
    "'; rm -rf / #",
    "$(cat /etc/passwd)",
    "`whoami`",
    "text:with:colons,and,commas",
    "line1\nline2\nline3",
    "한글 텍스트와 이모지 😀 그리고 'quotes' \"double\"",
    "a\\b\\c backslashes \\' \\\"",
]


def test_write_text_file_preserves_content_byte_for_byte(tmp_path):
    for snippet in MALICIOUS_SNIPPETS:
        path = write_text_file(str(tmp_path), snippet)
        with open(path, encoding="utf-8") as f:
            assert f.read() == snippet


def test_malicious_text_never_appears_in_built_argv(tmp_path):
    spec_dict = {
        "scenes": [
            {
                "duration": 2.0,
                "background": {"source": str(_make_dummy_image(tmp_path))},
                "texts": [{"content": snippet} for snippet in MALICIOUS_SNIPPETS],
                "subtitles": [{"text": snippet, "start": 0.0, "end": 1.0} for snippet in MALICIOUS_SNIPPETS],
            }
        ]
    }
    spec = VideoSpec.from_dict(spec_dict)
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))

    full_command_str = " ".join(built.argv)
    for snippet in MALICIOUS_SNIPPETS:
        assert snippet not in full_command_str, f"raw user text leaked into the ffmpeg command: {snippet!r}"

    # And it genuinely is an argv list, not a shell string, for every element.
    for element in built.argv:
        assert isinstance(element, str)


def test_text_file_paths_in_filtergraph_point_to_real_files_with_the_text(tmp_path):
    spec_dict = {
        "scenes": [
            {
                "duration": 2.0,
                "background": {"source": str(_make_dummy_image(tmp_path))},
                "texts": [{"content": "'; rm -rf / #"}],
            }
        ]
    }
    spec = VideoSpec.from_dict(spec_dict)
    built = build_render_command(spec, str(tmp_path), str(tmp_path / "out.mp4"))

    filter_complex = built.argv[built.argv.index("-filter_complex") + 1]
    assert "textfile=" in filter_complex

    # Extract the textfile path and confirm the dangerous content lives there,
    # verbatim, as file content rather than command syntax.
    start = filter_complex.index("textfile='") + len("textfile='")
    end = filter_complex.index("'", start)
    text_file_path = filter_complex[start:end]
    assert os.path.isfile(text_file_path)
    with open(text_file_path, encoding="utf-8") as f:
        assert f.read() == "'; rm -rf / #"


def _make_dummy_image(tmp_path):
    # A 1x1 PNG is enough for build_render_command, which never opens the
    # file itself (only ffmpeg does, at actual render time).
    path = tmp_path / "dummy.png"
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "53de0000000c4944415408d763f8ffff3f0005fe02fea739666500000000"
        "49454e44ae426082"
    )
    path.write_bytes(png_bytes)
    return path
