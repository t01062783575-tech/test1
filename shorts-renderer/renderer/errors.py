class RendererError(Exception):
    """Base class for all shorts-renderer errors."""


class SpecError(RendererError):
    """The input JSON video spec is structurally or semantically invalid."""


class AssetError(RendererError):
    """An input asset (background, voiceover, music, font) could not be fetched or read."""


class RenderTimeoutError(RendererError):
    """ffmpeg did not finish within the configured timeout."""


class RenderFailedError(RendererError):
    """ffmpeg exited with a non-zero status."""


class VerificationError(RendererError):
    """Post-render ffprobe verification found the output did not match the spec."""
