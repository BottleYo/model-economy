#!/usr/bin/env python3
"""Deterministically render the PNG screenshots referenced by plugin.json."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from render_social_preview import (
    AMBER,
    BACKGROUND,
    MUTED,
    PALETTE,
    RULE,
    TEAL,
    TEXT,
    draw_bitmap_text,
    save_indexed_png,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "plugins/model-economy/assets/screenshots"


def render_card(
    output: Path, name: str, mode: str, subtitle: str, rows: tuple[str, ...]
) -> None:
    image = Image.new("P", (1280, 800), BACKGROUND)
    image.putpalette(bytes(channel for color in PALETTE for channel in color))
    draw = ImageDraw.Draw(image)
    draw.line((80, 126, 1200, 126), fill=RULE, width=2)
    draw.rounded_rectangle((80, 174, 362, 228), radius=4, fill=AMBER)
    draw_bitmap_text(image, (80, 62), "MODEL ECONOMY", 6, TEXT, bold=True)
    draw_bitmap_text(image, (100, 190), mode, 3, BACKGROUND, bold=True)
    draw_bitmap_text(image, (80, 276), subtitle, 3, MUTED)
    top = 366
    for row in rows:
        draw.rectangle((80, top - 16, 96, top), fill=TEAL)
        draw_bitmap_text(image, (126, top - 24), row, 3, TEXT)
        top += 92
    save_indexed_png(image, output / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render_card(
        args.output_dir,
        "core-mode.png",
        "CORE MODE",
        "Skills work without local role files.",
        (
            "Simple standard and mechanical tasks use main agent.",
            "Native quality gates still apply.",
            "High risk work fails closed.",
        ),
    )
    render_card(
        args.output_dir,
        "enhanced-mode.png",
        "ENHANCED MODE",
        "Optional six role local configuration.",
        (
            "Strong decisions stay at policy level caps.",
            "Balanced handles implementation.",
            "Status remains read only.",
        ),
    )


if __name__ == "__main__":
    main()
