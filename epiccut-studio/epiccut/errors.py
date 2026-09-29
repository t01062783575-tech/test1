"""Typed exception hierarchy for EpicCut Studio.

Kept separate from the modules that raise them so any module can import
errors without import cycles, and so the CLI can catch a single base class.
"""


class EpicCutError(Exception):
    """Base class for all EpicCut Studio errors."""


class RecipeError(EpicCutError):
    """Recipe JSON is structurally or semantically invalid."""


class BinaryNotFoundError(EpicCutError):
    """A required external binary (ffmpeg/ffprobe) is not on PATH."""


class ProbeError(EpicCutError):
    """ffprobe failed or returned unusable data for a media file."""


class RenderError(EpicCutError):
    """ffmpeg failed during rendering."""


class RenderCancelled(EpicCutError):
    """Render was cancelled cooperatively via a cancel token."""


class QAError(EpicCutError):
    """Post-export quality assurance check failed."""
