"""Epic Surreal look presets: data only in Phase A.

Each preset is a dict of recipe-field overrides (enhancement / stabilization
/ flicker_reduction / rife / a suggested slow camera push-in flag) matched to
the spec's descriptions. Phase B turns `enhancement`/`stabilization`/
`flicker_reduction` into real ffmpeg filters in `command_builder.py`; Phase A
just needs these values to exist, be attachable to a Recipe, and round-trip
through the JSON schema like everything else.
"""

from __future__ import annotations

from dataclasses import replace

from epiccut.schema.recipe import EnhancementSettings, FlickerReductionSettings, Recipe, RIFESettings, StabilizationSettings


class EpicSurrealPreset:
    def __init__(
        self,
        name: str,
        description: str,
        enhancement: EnhancementSettings,
        stabilization: StabilizationSettings,
        flicker_reduction: FlickerReductionSettings,
        slow_push_in: bool = True,
    ):
        self.name = name
        self.description = description
        self.enhancement = enhancement
        self.stabilization = stabilization
        self.flicker_reduction = flicker_reduction
        self.slow_push_in = slow_push_in


# "Sacred Temple default look: very subtle warm grade, controlled highlights,
#  slight bloom, low film grain, mild vignette, very slow push-in, no
#  aggressive effects." — spec, verbatim intent captured in these values.
SACRED_TEMPLE = EpicSurrealPreset(
    name="sacred-temple",
    description="Very subtle warm grade, controlled highlights, slight bloom, low grain, mild vignette, slow push-in.",
    enhancement=EnhancementSettings(
        exposure=0.0, contrast=0.05, highlights=-0.15, shadows=0.05,
        saturation=0.05, temperature=0.08, tint=0.0, gamma=1.0,
        sharpen=0.0, denoise=0.05,
        vignette=0.20, bloom=0.15, grain=0.08, haze=0.0,
    ),
    stabilization=StabilizationSettings(enabled=True, preset="minimal"),
    flicker_reduction=FlickerReductionSettings(enabled=True, strength=0.25),
    slow_push_in=True,
)

COSMIC_MONUMENT = EpicSurrealPreset(
    name="cosmic-monument",
    description="Cooler, higher-contrast grade for monumental scale; deeper vignette, subtle bloom on light sources.",
    enhancement=EnhancementSettings(
        exposure=-0.05, contrast=0.12, highlights=-0.10, shadows=0.10,
        saturation=0.0, temperature=-0.05, tint=0.0, gamma=1.0,
        sharpen=0.05, denoise=0.05,
        vignette=0.30, bloom=0.25, grain=0.10, haze=0.05,
    ),
    stabilization=StabilizationSettings(enabled=True, preset="balanced"),
    flicker_reduction=FlickerReductionSettings(enabled=True, strength=0.3),
    slow_push_in=True,
)

LIMINAL_CATHEDRAL = EpicSurrealPreset(
    name="liminal-cathedral",
    description="Desaturated, hazy, high-key grade for empty/liminal architectural space.",
    enhancement=EnhancementSettings(
        exposure=0.10, contrast=-0.05, highlights=-0.05, shadows=0.15,
        saturation=-0.15, temperature=0.02, tint=0.0, gamma=1.05,
        sharpen=0.0, denoise=0.08,
        vignette=0.15, bloom=0.20, grain=0.06, haze=0.20,
    ),
    stabilization=StabilizationSettings(enabled=True, preset="minimal"),
    flicker_reduction=FlickerReductionSettings(enabled=True, strength=0.25),
    slow_push_in=True,
)

DREAM_LANDSCAPE = EpicSurrealPreset(
    name="dream-landscape",
    description="Soft, painterly grade for wide natural/surreal landscapes; gentle bloom and haze, minimal vignette.",
    enhancement=EnhancementSettings(
        exposure=0.05, contrast=0.0, highlights=-0.10, shadows=0.10,
        saturation=0.10, temperature=0.05, tint=-0.02, gamma=1.0,
        sharpen=0.0, denoise=0.05,
        vignette=0.10, bloom=0.20, grain=0.05, haze=0.15,
    ),
    stabilization=StabilizationSettings(enabled=True, preset="minimal"),
    flicker_reduction=FlickerReductionSettings(enabled=True, strength=0.2),
    slow_push_in=True,
)

# RIFE-interpolation companion preset for slow, mostly-static AI environmental
# footage that needs heavy retiming (per spec: "Create an Epic Surreal Smooth
# preset optimized for slow AI-generated environmental footage"). This only
# takes effect where RIFE is actually installed (RifeAdapter.is_available());
# elsewhere the recipe still renders correctly via plain FFmpeg retiming.
EPIC_SURREAL_SMOOTH_RIFE = RIFESettings(enabled=True, target_fps=60, strength=0.6)


EPIC_SURREAL_PRESETS: dict[str, EpicSurrealPreset] = {
    p.name: p for p in (SACRED_TEMPLE, COSMIC_MONUMENT, LIMINAL_CATHEDRAL, DREAM_LANDSCAPE)
}


def apply_preset_to_recipe(recipe: Recipe, preset_name: str) -> Recipe:
    """Return a new Recipe with the named preset's enhancement/stabilization/
    flicker_reduction fields applied. Raises KeyError for an unknown name."""
    preset = EPIC_SURREAL_PRESETS[preset_name]
    return replace(
        recipe,
        enhancement=preset.enhancement,
        stabilization=preset.stabilization,
        flicker_reduction=preset.flicker_reduction,
    )
