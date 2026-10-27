"""Safe handling of user-generated text (Hook/Caption/CTA/Script lines from
the Make.com data store) inside ffmpeg filter graphs.

The rule that eliminates escaping and shell-injection risk entirely:
**user text never appears inside an ffmpeg filter string or shell command.**
Every drawtext overlay and subtitle line is written to its own small UTF-8
temp file and referenced via drawtext's `textfile=<path>` option. The only
thing that goes into the filter-graph string is the temp file's *path*,
and that path is always one we generated ourselves (a hex UUID filename in
a directory we created) — never user-controlled, so it can't contain
characters that would break filter-string or shell syntax. Arbitrary text
(quotes, colons, backticks, `$(...)`, Korean, emoji, newlines) is simply
bytes inside a file; ffmpeg reads it as a file, not as a command.

Everything is invoked via `subprocess` argv lists (see runner.py) — there
is no shell anywhere in this codebase, which is the second half of the
"no shell command injection" requirement.
"""

from __future__ import annotations

import os
import uuid


def write_text_file(work_dir: str, text: str) -> str:
    """Write `text` (any Unicode content) to a new UTF-8 file in
    `work_dir` and return its path. The filename is always a plain hex
    UUID — independent of the text's content — so it is always safe to
    embed in an ffmpeg filter expression."""
    path = os.path.join(work_dir, f"text_{uuid.uuid4().hex}.txt")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


def escape_filtergraph_path(path: str) -> str:
    """Escape a path for safe embedding inside a single-quoted ffmpeg
    filter option (e.g. `drawtext=textfile='<this>'`). Per ffmpeg's filter
    string quoting rules, everything inside a single-quoted value is
    literal *except* a backslash or a single quote — commas and colons
    need no escaping there. Only ever applied to paths *we* generate (see
    module docstring), never to user text, but implemented defensively in
    case a caller ever passes a path with unusual characters (e.g. a
    literal single quote in a directory name chosen by whoever deploys
    this service)."""
    return path.replace("\\", "\\\\").replace("'", "'\\''")
